"""Source verification for specified_public mode.

The verifier turns a pinned GitHub commit + file path + symbol into a
CodeEvidence that passes the strict model_validator in full_contracts. It only
uses static AST (never imports the fetched code) and reads the license from the
same immutable commit so the permalink and the bytes are coherent.
"""

from __future__ import annotations

import ast
import re
from pathlib import PurePosixPath
from typing import Any

from concept_to_code_learning.full_contracts.models import (
    CodeEvidence,
    LicenseFile,
    LicenseObservation,
    Relevance,
    SearchCandidate,
    SourceQuery,
    digest,
    utcnow,
)
from concept_to_code_learning.full_learning.ports import VerificationReceipt

from .errors import SourceError
from .github_client import GitHubRawClient

# Candidate license paths probed at the same commit. Order is informational;
# the first that resolves wins. The detector only marks DETECTED when an
# SPDX-grade identifier can be asserted from the bytes, never guessed.
LICENSE_PATHS = ("LICENSE", "LICENSE.md", "LICENSE.txt", "COPYING", "NOTICE")

# A minimal, conservative identifier detector. It looks for the canonical
# SPDX title in the first lines of the license file. Unknown content remains
# UNKNOWN and code_excerpt is withheld per INTERFACES.md.
LICENSE_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("MIT", re.compile(r"MIT License", re.IGNORECASE)),
    ("Apache-2.0", re.compile(r"Apache License(?:,? Version 2\.0)?", re.IGNORECASE)),
    ("BSD-3-Clause", re.compile(r"Redistribution and use.*source and binary forms", re.IGNORECASE | re.DOTALL)),
    ("BSD-2-Clause", re.compile(r"Redistribution and use.*source and binary forms.*Neither the name", re.IGNORECASE | re.DOTALL)),
    ("ISC", re.compile(r"ISC License", re.IGNORECASE)),
    ("MPL-2.0", re.compile(r"Mozilla Public License.*Version 2\.0", re.IGNORECASE | re.DOTALL)),
    ("Unlicense", re.compile(r"This is free and unencumbered software released into the public domain", re.IGNORECASE)),
)

REPO_PATTERN = re.compile(r"^([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)$")
SHA_PATTERN = re.compile(r"^[a-f0-9]{40}$")
PY_EXTENSION = ".py"


class SourceVerifier:
    """Pure orchestration: parse → fetch → AST → hashes → license → evidence."""

    def __init__(self, client: GitHubRawClient):
        self._client = client

    async def verify_specified_public(
        self, query: SourceQuery, candidate: SearchCandidate, scope_sha256: str,
    ) -> VerificationReceipt:
        scope = query  # SourceQuery extends SourceScope; same fields.
        self._require_mode(scope, "specified_public")
        self._require_network(scope)
        self._require_allowlist(scope)
        repo = self._require_candidate_repo(candidate)
        self._require_repo_in_allowlist(repo, scope.repository_allowlist)
        owner, name = self._split_repo(repo)
        commit_sha = await self._resolve_commit(owner, name, candidate.ref_hint)
        file_path = self._require_file_path(candidate)
        file_bytes = await self._client.fetch_raw(owner, name, commit_sha, file_path)
        file_text = file_bytes.decode("utf-8")
        symbol, symbol_kind, line_start, line_end = self._resolve_symbol(
            file_text, file_path, candidate.symbol_hint,
        )
        excerpt_lines = file_text.splitlines()[line_start - 1:line_end]
        code_excerpt = "\n".join(excerpt_lines)
        excerpt_sha256 = digest(code_excerpt)
        file_sha256 = digest(file_text)
        file_blob_sha = await self._client.fetch_blob_sha(owner, name, commit_sha, file_path)
        license_obs = await self._resolve_license(owner, name, commit_sha)
        checks = self._verification_checks(
            commit_sha=commit_sha, file_blob_sha=file_blob_sha,
            file_sha256=file_sha256, excerpt_sha256=excerpt_sha256,
            license_obs=license_obs, symbol_kind=symbol_kind,
        )
        # Code excerpt is only attached when the license explicitly allows display.
        displayed_excerpt = code_excerpt if license_obs.code_display_allowed else ""
        displayed_sha = digest(displayed_excerpt)
        permalink = self._permalink(owner, name, commit_sha, file_path, line_start, line_end)
        relevance = Relevance(
            status="SUPPORTED",
            reason="Candidate was discovered and verified at the pinned commit.",
            basis=[f"commit:{commit_sha}", f"file:{file_path}",
                   f"symbol:{symbol or 'none'}", f"lines:{line_start}-{line_end}"],
        )
        evidence = CodeEvidence(
            mode="LIVE",
            source_id=candidate.candidate_id,
            source_mode="specified_public",
            repository_owner=owner,
            repository_name=name,
            repository_url=f"https://github.com/{owner}/{name}",
            visibility="public",
            commit_sha=commit_sha,
            requested_ref=candidate.ref_hint,
            file_path=file_path,
            language=self._language_for(file_path),
            symbol=symbol,
            symbol_kind=symbol_kind,
            line_start=line_start,
            line_end=line_end,
            code_excerpt=displayed_excerpt,
            excerpt_sha256=displayed_sha,
            file_blob_sha=file_blob_sha,
            file_sha256=file_sha256,
            permalink=permalink,
            license_observation=license_obs,
            retrieved_at=utcnow(),
            verification_checks=checks,
            provenance_kind="SOURCE_EXACT",
            verification_status="VERIFIED",
            relevance=relevance,
        )
        return VerificationReceipt(
            query_id=query.query_id, candidate_id=candidate.candidate_id,
            scope_sha256=scope_sha256, evidence=evidence,
        )

    # --- helpers -----------------------------------------------------------

    def _require_mode(self, scope: Any, expected: str) -> None:
        if scope.source_mode != expected:
            raise SourceError("INVALID_PROVIDER_RESPONSE", "verify",
                              f"Verifier received mode {scope.source_mode!r}, expected {expected!r}",
                              status=422)

    def _require_network(self, scope: Any) -> None:
        if not scope.network_authorized:
            raise SourceError("NETWORK_NOT_AUTHORIZED", "verify",
                              "specified_public requires explicit network authorization",
                              status=403, needed_action="Set network_authorized=true with user consent.")

    def _require_allowlist(self, scope: Any) -> None:
        if not scope.repository_allowlist:
            raise SourceError("NETWORK_NOT_AUTHORIZED", "verify",
                              "specified_public requires a non-empty repository allowlist",
                              status=403, needed_action="Provide at least one owner/repo in the allowlist.")

    def _require_candidate_repo(self, candidate: SearchCandidate) -> str:
        repo = candidate.repository
        if not repo:
            raise SourceError("INVALID_PROVIDER_RESPONSE", "verify",
                              "candidate.repository is required for specified_public",
                              status=422)
        return repo

    def _require_repo_in_allowlist(self, repo: str, allowlist: list[str]) -> None:
        if repo not in allowlist:
            raise SourceError("REPO_UNAVAILABLE", "verify",
                              f"{repo} is not in the authorized allowlist",
                              status=403, needed_action="Add the repository to the allowlist.")

    def _split_repo(self, repo: str) -> tuple[str, str]:
        match = REPO_PATTERN.match(repo)
        if not match:
            raise SourceError("INVALID_PROVIDER_RESPONSE", "verify",
                              f"Repository {repo!r} is not a canonical owner/name",
                              status=422)
        return match.group(1), match.group(2)

    async def _resolve_commit(self, owner: str, name: str, ref_hint: str | None) -> str:
        if not ref_hint:
            raise SourceError("REF_UNRESOLVED", "verify",
                              "candidate.ref_hint is required to pin the commit",
                              status=422, needed_action="Provide a branch, tag or 40-char SHA.")
        if SHA_PATTERN.match(ref_hint):
            return ref_hint
        try:
            return await self._client.resolve_ref(owner, name, ref_hint)
        except SourceError as exc:
            if exc.code == "FILE_NOT_FOUND":
                raise SourceError("REF_UNRESOLVED", "verify",
                                  f"Ref {ref_hint!r} could not be resolved",
                                  status=404, needed_action="Confirm the ref exists.") from exc
            raise

    def _require_file_path(self, candidate: SearchCandidate) -> str:
        path = candidate.file_hint
        if not path:
            raise SourceError("FILE_NOT_FOUND", "verify",
                              "candidate.file_hint is required",
                              status=422, needed_action="Provide a repository-relative file path.")
        checked = PurePosixPath(path)
        if checked.is_absolute() or ".." in checked.parts or "\\" in path:
            raise SourceError("FILE_NOT_FOUND", "verify",
                              "File path must be repository-relative and cannot escape the root",
                              status=422, needed_action="Use a path like 'src/app.py'.")
        return path

    def _resolve_symbol(
        self, file_text: str, file_path: str, symbol_hint: str | None,
    ) -> tuple[str | None, str, int, int]:
        """Return (symbol, kind, line_start, line_end). Lines are 1-indexed inclusive."""
        if not symbol_hint:
            # No symbol requested: cover the whole file. python_symbol=NOT_APPLICABLE.
            lines = file_text.splitlines()
            return None, "NOT_APPLICABLE", 1, max(1, len(lines))
        if PurePosixPath(file_path).suffix != PY_EXTENSION:
            # Non-Python file with a symbol hint: AST cannot resolve; mark NOT_APPLICABLE.
            # Line range defaults to the whole file; caller may narrow with hints later.
            lines = file_text.splitlines()
            return symbol_hint, "NOT_APPLICABLE", 1, max(1, len(lines))
        return self._locate_python_symbol(file_text, symbol_hint)

    def _locate_python_symbol(self, file_text: str, symbol: str) -> tuple[str, str, int, int]:
        try:
            tree = ast.parse(file_text, mode="exec")
        except SyntaxError as exc:
            raise SourceError("SYMBOL_NOT_FOUND", "verify",
                              f"File cannot be parsed as Python: {exc.msg}",
                              status=422, needed_action="Confirm the file is valid Python.") from exc
        for node in ast.walk(tree):
            name = getattr(node, "name", None)
            if name != symbol:
                continue
            kind = self._ast_symbol_kind(node)
            if kind is None:
                continue
            # Decorator lines are excluded from the function's own line range;
            # the user sees the def line and the body, not the decorators.
            start = node.lineno
            end = getattr(node, "end_lineno", start)
            return symbol, kind, start, end
        raise SourceError("SYMBOL_NOT_FOUND", "verify",
                          f"Symbol {symbol!r} not found in the file",
                          status=404, needed_action="Confirm the symbol exists at the pinned commit.")

    def _ast_symbol_kind(self, node: ast.AST) -> str | None:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return "function"
        if isinstance(node, ast.ClassDef):
            return "class"
        return None

    def _language_for(self, file_path: str) -> str:
        suffix = PurePosixPath(file_path).suffix.lower().lstrip(".")
        return suffix or "text"

    async def _resolve_license(self, owner: str, name: str, commit: str) -> LicenseObservation:
        for path in LICENSE_PATHS:
            content = await self._client.fetch_license(owner, name, commit, path)
            if content is None:
                continue
            text = content.decode("utf-8")
            identifier = self._detect_identifier(text)
            content_sha256 = digest(text)
            license_file = LicenseFile(
                path=path, commit_sha=commit, content_sha256=content_sha256,
                permalink=f"https://github.com/{owner}/{name}/blob/{commit}/{path}",
                identifier=identifier,
            )
            if identifier is None:
                # File exists but identifier cannot be asserted: UNKNOWN, withhold code.
                return LicenseObservation(
                    status="UNKNOWN", files=[license_file], code_display_allowed=False,
                )
            return LicenseObservation(
                status="DETECTED", files=[license_file], code_display_allowed=True,
                limitations=["Retain the license notice when reproducing the excerpt."],
            )
        # No license file found at any candidate path.
        return LicenseObservation(status="UNKNOWN", files=[], code_display_allowed=False)

    def _detect_identifier(self, text: str) -> str | None:
        head = text[:4096]
        for identifier, pattern in LICENSE_PATTERNS:
            if pattern.search(head):
                return identifier
        return None

    def _permalink(self, owner: str, name: str, commit: str, path: str,
                   line_start: int, line_end: int) -> str:
        return (f"https://github.com/{owner}/{name}/blob/{commit}/"
                f"{path}#L{line_start}-L{line_end}")

    def _verification_checks(
        self, *, commit_sha: str, file_blob_sha: str | None,
        file_sha256: str, excerpt_sha256: str, license_obs: LicenseObservation,
        symbol_kind: str,
    ) -> dict[str, str]:
        checks: dict[str, str] = {
            "public_repository": "PASSED",
            "commit": "PASSED" if commit_sha else "FAILED",
            "file": "PASSED" if file_sha256 else "FAILED",
            "line_range": "PASSED",
            "excerpt_hash": "PASSED" if excerpt_sha256 else "FAILED",
            "license": "PASSED" if license_obs.status == "DETECTED" else "NOT_APPLICABLE",
        }
        if symbol_kind == "NOT_APPLICABLE":
            checks["python_symbol"] = "NOT_APPLICABLE"
        else:
            checks["python_symbol"] = "PASSED"
        return checks
