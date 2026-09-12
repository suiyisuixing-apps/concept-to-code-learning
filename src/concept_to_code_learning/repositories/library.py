"""Pin GitHub trees and read files on demand. Never clone, import or execute them."""

import asyncio
import hashlib
import json
import posixpath
import re
import sqlite3
from contextlib import closing
from pathlib import PurePosixPath
from urllib.parse import quote, urlsplit

from concept_to_code_learning.full_contracts import models as m
from concept_to_code_learning.full_learning.errors import LearningError, require
from concept_to_code_learning.github_intelligence.verifier import LICENSE_PATHS, license_observation

from .models import OpenFile, Repository, TreeEntry, TreePage

MAX_BYTES = 1024 * 1024
REGULAR = {"100644": "file", "100755": "file", "040000": "folder",
           "120000": "symlink", "160000": "submodule"}


def repository_name(value):
    value = value.strip()
    if "://" in value:
        url = urlsplit(value)
        require(url.scheme == "https" and url.netloc == "github.com"
                and not url.query and not url.fragment, "INVALID_REPOSITORY", "repository",
                "请输入 GitHub 仓库地址，例如 github.com/owner/repo。", 422)
        value = url.path.strip("/")
    elif value.startswith("github.com/"):
        value = value.removeprefix("github.com/").rstrip("/")
    value = value.removesuffix(".git")
    require(bool(re.fullmatch(r"[A-Za-z0-9_-][A-Za-z0-9_.-]*/[A-Za-z0-9_-][A-Za-z0-9_.-]*", value)),
            "INVALID_REPOSITORY", "repository", "请输入 owner/repo 或完整 GitHub 仓库地址。", 422)
    return value


def safe_relative(path, *, empty=False):
    require((empty and path == "") or bool(path) and len(path) <= 1000
            and str(PurePosixPath(path)) == path and not path.startswith("/")
            and ".." not in PurePosixPath(path).parts and "\\" not in path
            and not any(ord(c) < 32 or ord(c) == 127 for c in path),
            "INVALID_PATH", "repository", "请选择仓库文件树中的路径。", 422)
    return path


def chunks(text):
    # Normalize only line endings. Original bytes and Git blob identity remain recorded.
    lines = text.splitlines()
    result, batch, length, start = [], [], 0, 1
    for line in lines:
        require(len(line) <= 16000, "FILE_TOO_LARGE", "repository",
                "此文件包含过长的压缩代码行，请在 GitHub 查看。", 413)
        if batch and (length + len(line) + 1 > 16000 or len(batch) >= 240):
            result.append((start, "\n".join(batch)))
            start += len(batch)
            batch, length = [], 0
        batch.append(line)
        length += len(line) + 1
    if batch:
        result.append((start, "\n".join(batch)))
    return result or [(1, "")]


def import_paths(text, path):
    """Static literal imports only. Returned hints still have to exist in the pinned tree."""
    parent = posixpath.dirname(path)
    hints = []
    if path.endswith(".py"):
        for relative, module in re.findall(r"^\s*from\s+(\.*)([\w.]*)\s+import\s+", text, re.M):
            base = parent if relative else ""
            for _ in relative[1:]:
                base = posixpath.dirname(base)
            stem = posixpath.join(base, module.replace(".", "/"))
            hints.extend((stem + ".py", stem + "/__init__.py"))
        for module in re.findall(r"^\s*import\s+([\w.]+)", text, re.M):
            stem = module.replace(".", "/")
            hints.extend((stem + ".py", stem + "/__init__.py"))
    for target in re.findall(r'''(?:from\s*|require\(\s*|import\s*)["'](\.[^"'\n]+)["']''', text):
        stem = posixpath.normpath(posixpath.join(parent, target))
        hints.extend([stem, *[stem + ext for ext in (".ts", ".tsx", ".js", ".jsx")],
                      *[stem + "/index" + ext for ext in (".ts", ".tsx", ".js", ".jsx")]])
    return list(dict.fromkeys(p for p in hints if not p.startswith("../")))


class RepositoryLibrary:
    def __init__(self, data_dir, client):
        self.client = client
        data_dir.mkdir(parents=True, exist_ok=True)
        self.path = data_dir / "repository-library.sqlite3"
        self._lock = asyncio.Lock()
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute("CREATE TABLE IF NOT EXISTS repositories (id TEXT PRIMARY KEY, body TEXT NOT NULL)")
            db.execute("CREATE TABLE IF NOT EXISTS trees (repo TEXT, directory TEXT, body TEXT NOT NULL, PRIMARY KEY(repo,directory))")
            db.execute("CREATE TABLE IF NOT EXISTS code_files (id TEXT PRIMARY KEY, body TEXT NOT NULL, body_hash TEXT NOT NULL)")

    def _read(self, table, key, value):
        # Table and key names are internal constants; values always use parameters.
        with closing(sqlite3.connect(self.path)) as db:
            row = db.execute(f"SELECT body{', body_hash' if table == 'code_files' else ''} FROM {table} WHERE {key}=?", (value,)).fetchone()
        if row and table == "code_files":
            require(m.digest(row[0]) == row[1], "SOURCE_MISMATCH", "repository", "本地源码快照校验失败。", 409)
        return json.loads(row[0]) if row else None

    def list(self):
        with closing(sqlite3.connect(self.path)) as db:
            rows = db.execute("SELECT body FROM repositories ORDER BY rowid DESC").fetchall()
        return [Repository.model_validate_json(row[0]) for row in rows]

    def get(self, repository_id):
        value = self._read("repositories", "id", repository_id)
        require(value is not None, "REPO_UNAVAILABLE", "repository", "请先加载这个仓库。", 404)
        return Repository.model_validate(value)

    async def add(self, request):
        name = repository_name(request.repository)
        async with self._lock:
            owner, repo_name = name.split("/")
            metadata = await self.client.repository(owner, repo_name)
            name = repository_name(metadata["full_name"])
            owner, repo_name = name.split("/")
            ref = request.ref or metadata["default_branch"]
            commit = await self.client.resolve_ref(owner, repo_name, ref)
            repository_id = "repo-" + m.digest(name.casefold() + ":" + commit)[:32]
            existing = self._read("repositories", "id", repository_id)
            if existing:
                return Repository.model_validate(existing)
            tree = await self.client.tree(owner, repo_name, commit)
            truncated = bool(tree.get("truncated"))
            if truncated:
                tree = await self.client.tree(owner, repo_name, commit, recursive=False)
                require(not tree.get("truncated"), "TREE_INCOMPLETE", "repository",
                        "GitHub 未能返回完整目录，请稍后重试。", 502)
            result = Repository(mode="LIVE", repository_id=repository_id, repository=name,
                description=str(metadata.get("description") or "")[:1000], ref=ref, commit_sha=commit,
                tree_sha=tree["sha"], complete_tree=not truncated, created_at=m.utcnow())
            grouped = self._tree_entries(tree, "", recursive=not truncated)
            with closing(sqlite3.connect(self.path)) as db, db:
                db.execute("INSERT INTO repositories VALUES (?,?)", (repository_id, result.model_dump_json()))
                for directory, entries in grouped.items():
                    db.execute("INSERT INTO trees VALUES (?,?,?)", (repository_id, directory,
                               json.dumps([e.model_dump() for e in entries], ensure_ascii=False)))
            return result

    @staticmethod
    def _tree_entries(tree, directory, *, recursive):
        require(isinstance(tree.get("tree"), list), "SOURCE_MISMATCH", "repository",
                "GitHub 文件树格式不正确。", 502)
        grouped, seen = {directory: []}, set()
        for raw in tree["tree"]:
            path = safe_relative(posixpath.join(directory, raw["path"]))
            require(path not in seen and raw.get("mode") in REGULAR,
                    "SOURCE_MISMATCH", "repository", "GitHub 文件树存在重复或不支持的条目。", 502)
            require(recursive or posixpath.dirname(path) == directory, "SOURCE_MISMATCH",
                    "repository", "GitHub 目录条目不匹配。", 502)
            seen.add(path)
            entry = TreeEntry(path=path, sha=raw["sha"], kind=REGULAR[raw["mode"]], size=raw.get("size", 0))
            grouped.setdefault(posixpath.dirname(path), []).append(entry)
            if recursive and entry.kind == "folder":
                grouped.setdefault(path, [])
        return grouped

    def _directory(self, repository_id, directory):
        with closing(sqlite3.connect(self.path)) as db:
            row = db.execute("SELECT body FROM trees WHERE repo=? AND directory=?", (repository_id, directory)).fetchone()
        return [TreeEntry.model_validate(e) for e in json.loads(row[0])] if row else None

    async def directory(self, repository_id, directory=""):
        safe_relative(directory, empty=True)
        repo = self.get(repository_id)
        cached = self._directory(repository_id, directory)
        if cached is not None:
            return cached
        # Resolve every ancestor through known tree entries. No client-supplied SHA is trusted.
        entry = await self.entry(repository_id, directory)
        require(entry.kind == "folder", "INVALID_PATH", "repository", "此路径不是文件夹。", 422)
        async with self._lock:
            cached = self._directory(repository_id, directory)
            if cached is not None:
                return cached
            owner, name = repo.repository.split("/")
            await self.client.repository(owner, name)
            tree = await self.client.tree(owner, name, entry.sha, recursive=False)
            require(tree.get("sha") == entry.sha and not tree.get("truncated"), "SOURCE_MISMATCH",
                    "repository", "目录版本不完整，请重试。", 502)
            entries = self._tree_entries(tree, directory, recursive=False)[directory]
            with closing(sqlite3.connect(self.path)) as db, db:
                db.execute("INSERT OR REPLACE INTO trees VALUES (?,?,?)", (repository_id, directory,
                           json.dumps([e.model_dump() for e in entries], ensure_ascii=False)))
            return entries

    async def entry(self, repository_id, path):
        safe_relative(path)
        entries = await self.directory(repository_id, posixpath.dirname(path))
        entry = next((e for e in entries if e.path == path), None)
        require(entry is not None, "FILE_NOT_FOUND", "repository", "此版本中没有这个文件。", 404)
        return entry

    async def tree(self, repository_id, directory="", query="", offset=0, limit=300):
        entries = await self.directory(repository_id, directory)
        repo = self.get(repository_id)
        if query.strip():
            with closing(sqlite3.connect(self.path)) as db:
                rows = db.execute("SELECT body FROM trees WHERE repo=?", (repository_id,)).fetchall()
            entries = [TreeEntry.model_validate(e) for row in rows for e in json.loads(row[0])
                       if query.casefold() in e["path"].casefold()]
        entries = sorted(entries, key=lambda e: (e.kind != "folder", e.path.casefold()))
        return TreePage(entries=entries[offset:offset + limit], directory=directory,
                        total=len(entries), offset=offset, complete_tree=repo.complete_tree)

    async def _bytes(self, repo, entry):
        require(entry.kind == "file", "UNSUPPORTED_FORMAT", "repository",
                "链接和子模块保留在目录中，请在 GitHub 查看其内容。", 422)
        require(entry.size <= MAX_BYTES, "FILE_TOO_LARGE", "repository",
                "文件超过 1 MiB 阅读上限，请在 GitHub 查看。", 413)
        owner, name = repo.repository.split("/")
        raw = await self.client.fetch_raw(owner, name, repo.commit_sha, entry.path)
        blob = hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()
        require(len(raw) == entry.size and blob == entry.sha, "SOURCE_MISMATCH", "repository",
                "源码字节与固定版本不匹配，已停止读取。", 502)
        return raw

    async def _license(self, repo, path):
        folders = list(reversed(PurePosixPath(path).parents))
        entries = []
        for folder in folders:
            directory = "" if str(folder) == "." else str(folder)
            entries.extend(e for e in await self.directory(repo.repository_id, directory)
                           if PurePosixPath(e.path).name.casefold() in {p.casefold() for p in LICENSE_PATHS})
        require(len(entries) <= 12, "LICENSE_UNKNOWN", "repository", "许可文件过多，暂不展开源码。", 422)
        observed = []
        for entry in entries:
            raw = await self._bytes(repo, entry)
            observed.append((entry.path, raw, repo.commit_sha,
                             f"https://github.com/{repo.repository}/blob/{repo.commit_sha}/{quote(entry.path, safe='/')}"))
        return license_observation(observed)

    @staticmethod
    def _decode(raw):
        try:
            text = raw.decode("utf-8-sig")
        except UnicodeError:
            raise LearningError("UNSUPPORTED_FORMAT", "repository", "这是二进制或非 UTF-8 文件，请在 GitHub 查看。", 422) from None
        require(not any(ord(c) < 32 and c not in "\n\r\t" for c in text),
                "UNSUPPORTED_FORMAT", "repository", "此资源不适合文本阅读，请在 GitHub 查看。", 422)
        return text

    @staticmethod
    def _location(repo, entry, start, end):
        return m.CodeLocation(repository_id=repo.repository_id, repository=repo.repository,
            commit_sha=repo.commit_sha, file_path=entry.path, blob_sha=entry.sha,
            line_start=start, line_end=max(start, end))

    async def open_file(self, repository_id, path):
        repo = self.get(repository_id)
        safe_relative(path)
        document_id = "code-" + m.digest(repository_id + ":" + path)[:40]
        cached = self._read("code_files", "id", document_id)
        if cached:
            return OpenFile.model_validate(cached)
        owner, name = repo.repository.split("/")
        await self.client.repository(owner, name)
        entry = await self.entry(repository_id, path)
        # Check format/size before any content request, including symlinks/submodules.
        require(entry.kind == "file" and entry.size <= MAX_BYTES, "UNSUPPORTED_FORMAT", "repository",
                "此条目是链接、子模块或大文件，请在 GitHub 查看。", 422)
        license = await self._license(repo, path)
        require(license.code_display_allowed, "LICENSE_UNKNOWN", "repository",
                "未确认此文件的源码展示许可，可在 GitHub 阅读原文件。", 422)
        raw = await self._bytes(repo, entry)
        text = self._decode(raw)
        split = chunks(text)
        location = self._location(repo, entry, 1, len(text.splitlines()))
        record = m.DocumentRecord(mode="LIVE", document_id=document_id,
            file_name=PurePosixPath(path).name[:240], source_type="CODE", original_sha256=hashlib.sha256(raw).hexdigest(),
            unit_count=len(split), import_status="READY" if text.strip() else "NO_EXTRACTABLE_TEXT",
            created_at=m.utcnow(), capabilities=["code-reading", "selection", "annotations"],
            code_location=location, code_license=license)
        supporting, warnings = [], []
        for hint in import_paths(text[:32000], path)[:16]:
            if hint == path or len(supporting) == 2:
                continue
            try:
                other = await self.entry(repository_id, hint)
                if other.kind != "file" or other.size > MAX_BYTES:
                    continue
                permission = await self._license(repo, hint)
                if not permission.code_display_allowed:
                    continue
                related = self._decode(await self._bytes(repo, other))
                lines, count = [], 0
                for line in related.splitlines():
                    if count + len(line) + 1 > 4000:
                        break
                    lines.append(line)
                    count += len(line) + 1
                if not lines:
                    continue
                supporting.append(m.Block(block_id="related-" + m.digest(hint)[:24], kind="code",
                    text="\n".join(lines), source_locator=m.SourceLocator(unit_type="section", index=1),
                    code_location=self._location(repo, other, 1, len(lines)), code_license=permission))
            except LearningError as exc:
                if exc.code in {"FILE_NOT_FOUND", "INVALID_PATH", "UNSUPPORTED_FORMAT", "LICENSE_UNKNOWN"}:
                    continue
                if exc.code == "SOURCE_MISMATCH":
                    raise
                # A failed related read is visible; the current file remains usable.
                warnings.append("部分关联文件读取失败，本次仅依据已读取的代码。")
                break
        units = []
        for index, (start, content) in enumerate(split, 1):
            locator = m.SourceLocator(unit_type="section", index=index, heading_path=[path])
            units.append(m.DocumentUnit(mode="LIVE", document_id=document_id, document_revision=1,
                unit_id=f"{document_id}.{index}", unit_type="section", index=index, heading_path=[path],
                source_locator=locator, blocks=[m.Block(block_id=f"{document_id}.{index}.code", kind="code",
                    text=content, source_locator=locator,
                    code_location=self._location(repo, entry, start, start + content.count("\n")), code_license=license)],
                supporting_blocks=supporting, preview=m.Preview(kind="learning_view", fidelity="extracted"),
                warnings=list(dict.fromkeys(warnings)),
                extraction_status="READY" if content.strip() else "NO_EXTRACTABLE_TEXT"))
        value = OpenFile(document=record, units=units)
        with closing(sqlite3.connect(self.path)) as db, db:
            body = value.model_dump_json()
            db.execute("INSERT OR IGNORE INTO code_files VALUES (?,?,?)", (document_id, body, m.digest(body)))
        # Concurrent reads use the first frozen snapshot, never replace a note's origin.
        return self.document(document_id)

    def document(self, document_id):
        value = self._read("code_files", "id", document_id)
        require(value is not None, "FILE_NOT_FOUND", "repository", "请先打开这个源码文件。", 404)
        return OpenFile.model_validate(value)

    async def close(self):
        await self.client.close()
