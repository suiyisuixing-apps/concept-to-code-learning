"""Shared fixtures for github_intelligence tests.

Tests never touch the network. A FakeGitHubRawClient returns frozen bytes
pinned to a fixed commit so the verifier exercises the real AST, hash and
license logic without any HTTP. The fixture mirrors the shape of the FastAPI
dependency-injection tutorial referenced in the repo's existing fixtures.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from concept_to_code_learning.github_intelligence.errors import SourceError
from concept_to_code_learning.github_intelligence.github_client import GitHubRawClient

# A frozen, immutable commit used across all tests. Any 40-hex SHA works; this
# one mirrors the repo convention of referencing fastapi's pinned example.
FROZEN_COMMIT = "50113da16fec53b66b80d75e80a89296de4fa5a5"
FROZEN_OWNER = "fastapi"
FROZEN_REPO = "fastapi"
FROZEN_REPO_SLUG = "fastapi/fastapi"
FROZEN_FILE = "docs_src/dependencies/tutorial001.py"

# 14-line file; read_items spans L12-L14 (def + docstring + return) so the
# AST end_lineno is 14 and the excerpt has exactly 3 lines, matching the
# CodeEvidence model_validator (line_end - line_start + 1 == excerpt lines).
FROZEN_FILE_TEXT = """from fastapi import Depends, FastAPI

app = FastAPI()


# Declare a dependency
def common_parameters(q: str | None = None, skip: int = 0, limit: int = 100):
    return {"q": q, "skip": skip, "limit": limit}


@app.get("/items/")
async def read_items(commons: dict = Depends(common_parameters)):
    \"\"\"Return the common parameters.\"\"\"
    return commons
"""

# Minimal MIT license text that the detector pattern matches as MIT.
FROZEN_LICENSE_TEXT = """MIT License

Copyright (c) 2026 fastapi

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND.
"""

FROZEN_BLOB_SHA = "a" * 40  # Placeholder git blob SHA returned by the fake API.


class FakeGitHubRawClient(GitHubRawClient):
    """In-memory client that returns frozen bytes; never opens a socket."""

    def __init__(self, *, license_text: str | None = FROZEN_LICENSE_TEXT,
                 file_text: str | None = FROZEN_FILE_TEXT,
                 blob_sha: str | None = FROZEN_BLOB_SHA,
                 file_missing: bool = False,
                 license_missing: bool = False,
                 ref_missing: bool = False):
        # Intentionally skip the parent __init__ so no httpx client is built.
        self._token = None
        self._timeout = 10.0
        self._retries = 0
        self._client = None
        self._license_text = license_text
        self._file_text = file_text
        self._blob_sha = blob_sha
        self._file_missing = file_missing
        self._license_missing = license_missing
        self._ref_missing = ref_missing

    async def fetch_raw(self, owner: str, name: str, commit: str, path: str) -> bytes:
        if self._file_missing or self._file_text is None:
            raise SourceError("FILE_NOT_FOUND", "fetch_raw",
                              "The requested path was not found at the pinned commit",
                              status=404)
        return self._file_text.encode("utf-8")

    async def resolve_ref(self, owner: str, name: str, ref: str) -> str:
        if self._ref_missing:
            raise SourceError("FILE_NOT_FOUND", "resolve_ref",
                              "Ref not found", status=404)
        # Any ref resolves to the frozen commit for test purposes.
        return FROZEN_COMMIT

    async def fetch_blob_sha(self, owner: str, name: str, commit: str, path: str) -> str | None:
        if self._file_missing:
            return None
        return self._blob_sha

    async def fetch_license(self, owner: str, name: str, commit: str, path: str) -> bytes | None:
        if self._license_missing or self._license_text is None:
            return None
        return self._license_text.encode("utf-8")

    async def close(self) -> None:
        return None


@pytest.fixture
def fake_client() -> FakeGitHubRawClient:
    return FakeGitHubRawClient()


@pytest.fixture
def fake_client_no_license() -> FakeGitHubRawClient:
    return FakeGitHubRawClient(license_text=None, license_missing=True)


@pytest.fixture
def fake_client_file_missing() -> FakeGitHubRawClient:
    return FakeGitHubRawClient(file_text=None, file_missing=True)


@pytest.fixture
def fake_client_ref_missing() -> FakeGitHubRawClient:
    return FakeGitHubRawClient(ref_missing=True)


def make_query(
    *,
    source_mode: str = "specified_public",
    repository_allowlist: list[str] | None = None,
    network_authorized: bool = True,
    concept_terms: list[str] | None = None,
    query_id: str = "q-test-1",
    status: str = "AUTHORIZED",
) -> Any:
    """Build a SourceQuery for tests without touching the Pydantic factory."""
    from concept_to_code_learning.full_contracts.models import (
        ScopeLimit,
        SourceQuery,
    )
    # local_authorized forbids network_authorized per SourceScope.local_boundary.
    if source_mode == "local_authorized":
        network_authorized = False
    return SourceQuery(
        mode="FIXTURE",
        query_id=query_id,
        question="How does FastAPI dependency injection work?",
        concept_terms=concept_terms or ["dependency injection", "Depends"],
        status=status,
        source_mode=source_mode,
        repository_allowlist=repository_allowlist if repository_allowlist is not None
            else [FROZEN_REPO_SLUG],
        local_handle=None,
        language_hint="python",
        scope_limit=ScopeLimit(),
        network_authorized=network_authorized,
        query_terms_approved=False,
        approved_query_terms=[],
        max_sources=3,
    )


def make_candidate(
    *,
    candidate_id: str = "c-test-1",
    query_id: str = "q-test-1",
    source_mode: str = "specified_public",
    repository: str | None = FROZEN_REPO_SLUG,
    ref_hint: str | None = FROZEN_COMMIT,
    file_hint: str | None = FROZEN_FILE,
    symbol_hint: str | None = "read_items",
    discovery_status: str = "CANDIDATE",
) -> Any:
    """Build a SearchCandidate for tests."""
    from concept_to_code_learning.full_contracts.models import SearchCandidate, utcnow
    return SearchCandidate(
        mode="FIXTURE",
        candidate_id=candidate_id,
        query_id=query_id,
        source_mode=source_mode,
        repository=repository,
        local_handle=None,
        ref_hint=ref_hint,
        file_hint=file_hint,
        symbol_hint=symbol_hint,
        matched_terms=["dependency injection"],
        ranking_reason="Allowlisted repository; user-selected ref/file/symbol.",
        discovery_method="allowlist_framework",
        discovery_status=discovery_status,
        retrieved_at=utcnow(),
    )


@pytest.fixture
def authorized_local_root(tmp_path: Path) -> Path:
    """A clean tmp directory that the registry can be authorized to read."""
    root = tmp_path / "local-repo"
    root.mkdir()
    (root / "README.md").write_text("# local repo\n", encoding="utf-8")
    return root
