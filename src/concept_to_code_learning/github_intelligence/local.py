"""Read-only local discovery with exact working-file hashes and no remote requests."""

import asyncio
import hashlib
import os
import shutil
from pathlib import PurePosixPath

from concept_to_code_learning.full_contracts import models as m
from concept_to_code_learning.full_learning.io import run_io
from concept_to_code_learning.full_learning.ports import VerificationReceipt

from .discovery import EXTENSIONS, candidate, matched, ranked_paths, result
from .errors import SourceError
from .verifier import LICENSE_PATHS, excerpt, license_observation


async def git(root, *args, optional=False):
    env = {
        "PATH": os.environ.get("PATH", os.defpath),
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_TERMINAL_PROMPT": "0",
        "GIT_OPTIONAL_LOCKS": "0",
        "LC_ALL": "C",
    }
    env.update({k: os.environ[k] for k in ("SYSTEMROOT", "WINDIR", "TEMP", "TMP") if k in os.environ})
    executable = shutil.which("git")
    if not executable:
        raise SourceError("REPO_UNAVAILABLE", "local", "未安装 Git。", 503)
    process = await asyncio.create_subprocess_exec(
        executable,
        "-c",
        "core.fsmonitor=false",
        "-c",
        "core.hooksPath=" + os.devnull,
        "-C",
        str(root),
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.DEVNULL,
        env=env,
    )
    try:
        async with asyncio.timeout(5):
            # Bound even unusually large indexes/blobs; never run filters, hooks or diff tools.
            chunks, size = [], 0
            while chunk := await process.stdout.read(65536):
                size += len(chunk)
                if size > 2 * 1024 * 1024:
                    raise SourceError("REPO_UNAVAILABLE", "local", "本地索引超过检索上限。", 413)
                chunks.append(chunk)
            data = b"".join(chunks)
            await process.wait()
    except BaseException:
        if process.returncode is None:
            process.kill()
            await process.wait()
        raise
    if process.returncode and not optional:
        raise SourceError("REPO_UNAVAILABLE", "local", "授权目录不是可读取的 Git 仓库。", 422)
    return b"" if process.returncode else data


class LocalSources:
    def __init__(self, registry):
        self.registry = registry

    def root(self, query):
        root = self.registry.root_for(query.local_handle)
        if root is None or query.network_authorized:
            raise SourceError("AUTH_REQUIRED", "local", "本地仓库授权已失效。", 403)
        return root

    async def search(self, query):
        root = self.root(query)
        # Only tracked files are considered, excluding accidental secrets and arbitrary home files.
        files = (await git(root, "ls-files", "-z")).decode("utf-8").split("\0")
        candidates, warnings = [], []
        for path in ranked_paths(files, query.concept_terms, query.language_hint)[
            : query.scope_limit.files
        ]:
            try:
                raw = await run_io(self.registry.read, query.local_handle, path)
                text = raw.decode("utf-8")
            except (OSError, UnicodeError, SourceError):
                warnings.append("一个不可安全读取的本地文件已跳过。")
                continue
            value = candidate(query, None, query.local_handle, None, path, text)
            if value:
                # Bind discovery bytes; verify refuses a file modified after search.
                value.ref_hint = "sha256:" + hashlib.sha256(raw).hexdigest()
                candidates.append(value)
        candidates.sort(key=lambda c: -len(c.matched_terms))
        return result(query, candidates, warnings)

    async def verify(self, query, candidate, scope_sha256):
        root = self.root(query)
        if candidate.local_handle != query.local_handle or candidate.query_id != query.query_id:
            raise SourceError("SOURCE_MISMATCH", "local", "本地候选与检索不匹配。", 409)
        path = candidate.file_hint
        raw = await run_io(self.registry.read, query.local_handle, path)
        file_hash = hashlib.sha256(raw).hexdigest()
        if candidate.ref_hint != "sha256:" + file_hash:
            raise SourceError("SOURCE_MISMATCH", "local", "文件在检索后发生变化，请重新检索。", 409)
        text = raw.decode("utf-8")
        kind, start, end, code = excerpt(text, path, candidate.symbol_hint, query.concept_terms)
        commit = (
            await git(root, "rev-parse", "--verify", "HEAD", optional=True)
        ).decode().strip() or None
        # HEAD can move between commands. Compare against the exact recorded
        # revision so a concurrent checkout cannot mislabel working bytes as clean.
        committed = await git(root, "show", commit + ":" + path, optional=True) if commit else b""
        dirty = not commit or committed != raw
        folders = (
            [PurePosixPath(".")]
            + list(PurePosixPath(path).parent.parents)
            + [PurePosixPath(path).parent]
        )
        entries = []
        for item in dict.fromkeys(
            str(folder / name) for folder in folders for name in LICENSE_PATHS
        ):
            try:
                content = await run_io(self.registry.read, query.local_handle, item)
            except (OSError, SourceError):
                continue
            entries.append((item, content, None, None))
        license = license_observation(entries)
        hits = matched(code, query.concept_terms)
        displayed = code if license.code_display_allowed else ""
        checks = {k: "PASSED" for k in ("scope", "file", "line_range", "excerpt_hash")}
        checks.update(
            license="PASSED" if displayed else "NOT_CHECKED",
            commit="PASSED" if commit else "NOT_APPLICABLE",
            python_symbol="PASSED" if kind != "NOT_APPLICABLE" else "NOT_APPLICABLE",
            public_remote="NOT_CHECKED",
        )
        evidence = m.CodeEvidence(
            mode="LIVE",
            source_id=candidate.candidate_id,
            source_mode="local_authorized",
            visibility="local",
            local_handle=query.local_handle,
            dirty=dirty,
            commit_sha=commit,
            requested_ref=candidate.ref_hint,
            file_path=path,
            language=EXTENSIONS.get(PurePosixPath(path).suffix.lower(), "text"),
            symbol=candidate.symbol_hint,
            symbol_kind=kind,
            line_start=start,
            line_end=end,
            code_excerpt=displayed,
            excerpt_sha256=m.digest(displayed),
            file_sha256=file_hash,
            license_observation=license,
            retrieved_at=m.utcnow(),
            verification_checks=checks,
            provenance_kind="SOURCE_EXACT",
            verification_status="VERIFIED" if displayed else "NEEDS_CONFIRMATION",
            relevance=m.Relevance(
                status="CANDIDATE" if hits else "UNCERTAIN",
                reason="本地原始文件已核验；未执行该代码。" if hits else "文件字节已核验，但片段未匹配当前知识点。",
                basis=hits,
            ),
        )
        return VerificationReceipt(query.query_id, candidate.candidate_id, scope_sha256, evidence)
