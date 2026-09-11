"""Verify immutable file bytes, real line ranges and observed license files."""

import ast
import hashlib
import re
from pathlib import PurePosixPath
from urllib.parse import quote

from concept_to_code_learning.full_contracts import models as m
from concept_to_code_learning.full_learning.ports import VerificationReceipt
from concept_to_code_learning.learning_concepts import guide_for, guide_for_terms

from .discovery import EXTENSIONS, matched, python_symbols
from .errors import SourceError
from .github_client import safe_path

LICENSE_PATHS = tuple(name + suffix for name in ("LICENSE", "LICENCE", "COPYING")
                      for suffix in ("", ".md", ".txt", ".rst"))


def detect_identifier(text):
    value = " ".join(text.casefold().split())
    if (
        "permission is hereby granted, free of charge" in value
        and "the software is provided" in value
    ):
        return "MIT"
    if "apache license" in value and "version 2.0" in value and "terms and conditions" in value:
        return "Apache-2.0"
    if (
        "redistribution and use in source and binary forms" in value
        and "this software is provided" in value
    ):
        return "BSD-3-Clause" if "neither the name" in value else "BSD-2-Clause"
    if (
        "permission to use, copy, modify, and/or distribute" in value
        and "the software is provided" in value
    ):
        return "ISC"
    if "this is free and unencumbered software released into the public domain" in value:
        return "Unlicense"
    return None


def excerpt(text, path, symbol, terms):
    lines = text.splitlines()
    if not lines:
        raise SourceError("NO_RELEVANT_SOURCE", "verify", "源码文件为空。", 422)
    kind = "NOT_APPLICABLE"
    if symbol and PurePosixPath(path).suffix.lower() == ".py":
        found = [x for x in python_symbols(text) if x[0] == symbol]
        if not found:
            raise SourceError("SYMBOL_NOT_FOUND", "verify", "固定版本中找不到候选符号。", 404)
        _, kind, start, end = found[0]
    else:
        guide = guide_for_terms(terms) or guide_for(" ".join(terms))
        terms = list(dict.fromkeys([*terms, *(guide.terms if guide else ())]))
        index = next((i for i, line in enumerate(lines) if matched(line, terms)), 0)
        if PurePosixPath(path).suffix.lower() == ".py":
            try:
                # Center teaching examples on executable statements, not the opening
                # gallery docstring. This is static parsing, never execution.
                nodes = ast.parse(text).body
                positions = [node.lineno - 1 for node in nodes
                             if isinstance(node, (ast.Assign, ast.AnnAssign, ast.Expr))
                             and not (isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant))
                             and matched("\n".join(lines[node.lineno - 1:node.end_lineno]), terms)]
                if positions:
                    index = positions[0]
            except (SyntaxError, ValueError, RecursionError):
                pass
        window = 36 if PurePosixPath(path).suffix.lower() == ".py" else 96
        start, end = max(1, index - 12), min(len(lines), index + window)
    # A joined trailing empty line is interpreted as a line terminator by
    # splitlines(), not another line. Keep the displayed inclusive range exact.
    while end > start and lines[end - 1] == "":
        end -= 1
    code = "\n".join(lines[start - 1 : end])
    if len(code) > 20000:
        raise SourceError(
            "NO_RELEVANT_SOURCE", "verify", "匹配符号超过片段上限，请缩小概念范围。", 422
        )
    return kind, start, end, code


def license_observation(entries):
    files = [
        m.LicenseFile(
            path=path,
            commit_sha=commit,
            content_sha256=hashlib.sha256(raw).hexdigest(),
            permalink=link,
            identifier=detect_identifier(raw.decode("utf-8", errors="replace")),
        )
        for path, raw, commit, link in entries
    ]
    identifiers = {f.identifier for f in files}
    detected = bool(files) and None not in identifiers and len(identifiers) == 1
    status = "DETECTED" if detected else ("MIXED" if len(identifiers) > 1 else "UNKNOWN")
    return m.LicenseObservation(
        status=status,
        files=files,
        code_display_allowed=detected,
        limitations=["记录已读取的许可文件；保留作者和许可声明。未对所有依赖或例外进行法律审查。"],
    )


class SourceVerifier:
    def __init__(self, client):
        self._client = client

    async def verify_specified_public(self, query, candidate, scope_sha256):
        if (
            query.source_mode not in {"specified_public", "public_search"}
            or not query.network_authorized
        ):
            raise SourceError(
                "NETWORK_NOT_AUTHORIZED", "verify", "当前范围不允许公开仓库读取。", 403
            )
        repo = candidate.repository
        if not repo or (
            query.source_mode == "specified_public" and repo not in query.repository_allowlist
        ):
            raise SourceError("REPO_UNAVAILABLE", "verify", "候选不在指定仓库范围内。", 403)
        if candidate.query_id != query.query_id or candidate.source_mode != query.source_mode:
            raise SourceError("SOURCE_MISMATCH", "verify", "候选不属于本次检索。", 409)
        owner, name = repo.split("/", 1)
        await self._client.repository(owner, name)
        if not candidate.ref_hint:
            raise SourceError("REF_UNRESOLVED", "verify", "候选缺少版本信息。", 422)
        try:
            commit = await self._client.resolve_ref(owner, name, candidate.ref_hint)
        except SourceError as exc:
            if exc.code == "FILE_NOT_FOUND":
                raise SourceError("REF_UNRESOLVED", "verify", "候选版本无法解析。", 404) from None
            raise
        if re.fullmatch(r"[a-f0-9]{40}", candidate.ref_hint) and commit != candidate.ref_hint:
            raise SourceError("SOURCE_MISMATCH", "verify", "返回版本与候选不符。", 502)
        path = candidate.file_hint
        safe_path(path)
        raw = await self._client.fetch_raw(owner, name, commit, path)
        try:
            text = raw.decode("utf-8")
        except UnicodeError:
            raise SourceError(
                "NO_RELEVANT_SOURCE", "verify", "源码不是支持的 UTF-8 文本。", 422
            ) from None
        kind, start, end, code = excerpt(text, path, candidate.symbol_hint, query.concept_terms)
        blob = await self._client.fetch_blob_sha(owner, name, commit, path)
        actual_blob = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
        if blob != actual_blob:
            raise SourceError("SOURCE_MISMATCH", "verify", "下载文件与 Git blob 标识不一致。", 502)
        license = await self._resolve_license(owner, name, commit, path)
        displayed = code if license.code_display_allowed else ""
        repo_url = f"https://github.com/{repo}"
        checks = {
            k: "PASSED"
            for k in ("public_repository", "commit", "file", "line_range", "excerpt_hash", "scope")
        }
        checks["license"] = "PASSED" if license.code_display_allowed else "NOT_CHECKED"
        checks["python_symbol"] = "PASSED" if kind != "NOT_APPLICABLE" else "NOT_APPLICABLE"
        hits = matched(code, query.concept_terms)
        evidence = m.CodeEvidence(
            mode="LIVE",
            source_id=candidate.candidate_id,
            source_mode=query.source_mode,
            repository_owner=owner,
            repository_name=name,
            repository_url=repo_url,
            visibility="public",
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
            file_blob_sha=blob,
            file_sha256=hashlib.sha256(raw).hexdigest(),
            permalink=f"{repo_url}/blob/{commit}/{quote(path, safe='/')}#L{start}-L{end}",
            license_observation=license,
            retrieved_at=m.utcnow(),
            verification_checks=checks,
            provenance_kind="SOURCE_EXACT",
            verification_status="VERIFIED" if displayed else "NEEDS_CONFIRMATION",
            relevance=m.Relevance(
                status="CANDIDATE" if hits else "UNCERTAIN",
                reason="固定文件与符号已核验；概念词匹配只提供相关性线索，不证明教学结论。",
                basis=hits,
            ),
        )
        return VerificationReceipt(query.query_id, candidate.candidate_id, scope_sha256, evidence)

    async def _resolve_license(self, owner, name, commit, file_path="source.py"):
        tree = await self._client.tree(owner, name, commit)
        paths = {
            x["path"]
            for x in tree.get("tree", [])
            if x.get("type") == "blob" and x.get("mode") in {"100644", "100755"}
        }
        ancestors = [PurePosixPath(".")] + list(reversed(PurePosixPath(file_path).parent.parents))
        ancestors += [PurePosixPath(file_path).parent]
        folders = {str(folder) for folder in ancestors}
        names = {name.casefold() for name in LICENSE_PATHS}
        candidates = sorted(p for p in paths if str(PurePosixPath(p).parent) in folders
                            and PurePosixPath(p).name.casefold() in names)[:12]
        entries = []
        for path in candidates:
            raw = await self._client.fetch_license(owner, name, commit, path)
            if raw is not None:
                entries.append(
                    (
                        path,
                        raw,
                        commit,
                        f"https://github.com/{owner}/{name}/blob/{commit}/{quote(path, safe='/')}",
                    )
                )
        observation = license_observation(entries)
        if tree.get("truncated"):
            observation.status = "UNKNOWN"
            observation.code_display_allowed = False
            observation.limitations.append("文件树被截断，无法确认目录许可覆盖。")
        return observation

    def _detect_identifier(self, text):
        return detect_identifier(text)
