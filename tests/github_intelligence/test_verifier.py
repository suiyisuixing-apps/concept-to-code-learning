"""Verifier tests: specified_public happy path and failure cases.

All tests run offline with a FakeGitHubRawClient. The frozen commit, file and
license bytes are defined in conftest.py and mirror the shape of the FastAPI
dependency-injection tutorial referenced elsewhere in the repo.
"""

from __future__ import annotations

import asyncio
import hashlib

import pytest

from concept_to_code_learning.github_intelligence.errors import SourceError
from concept_to_code_learning.github_intelligence.verifier import SourceVerifier

from .conftest import (
    FROZEN_BLOB_SHA,
    FROZEN_COMMIT,
    FROZEN_FILE,
    FROZEN_FILE_TEXT,
    FROZEN_OWNER,
    FROZEN_REPO,
    make_candidate,
    make_query,
)

SCOPE_SHA256 = "a" * 64  # Lead-supplied; any 64-hex string is structurally valid.


def run(coro):
    """Run an async coroutine in a fresh event loop (no pytest-asyncio needed)."""
    return asyncio.run(coro)


@pytest.fixture
def verifier(fake_client) -> SourceVerifier:
    return SourceVerifier(fake_client)


class TestVerifyHappyPath:
    """The fully-authorized case: commit pinned, file fetched, AST resolved, license MIT."""

    def test_returns_receipt_with_verified_evidence(self, verifier):
        query = make_query()
        candidate = make_candidate()
        receipt = run(verifier.verify_specified_public(query, candidate, SCOPE_SHA256))
        evidence = receipt.evidence
        assert receipt.query_id == query.query_id
        assert receipt.candidate_id == candidate.candidate_id
        assert receipt.scope_sha256 == SCOPE_SHA256
        assert evidence.source_mode == "specified_public"
        assert evidence.repository_owner == FROZEN_OWNER
        assert evidence.repository_name == FROZEN_REPO
        assert evidence.repository_url == f"https://github.com/{FROZEN_OWNER}/{FROZEN_REPO}"
        assert evidence.visibility == "public"
        assert evidence.commit_sha == FROZEN_COMMIT
        assert evidence.requested_ref == FROZEN_COMMIT
        assert evidence.file_path == FROZEN_FILE
        assert evidence.language == "py"
        assert evidence.symbol == "read_items"
        assert evidence.symbol_kind == "function"
        assert evidence.line_start == 12
        assert evidence.line_end == 14
        expected_excerpt = "\n".join(FROZEN_FILE_TEXT.splitlines()[11:14])
        assert evidence.code_excerpt == expected_excerpt
        assert evidence.excerpt_sha256 == hashlib.sha256(
            expected_excerpt.encode("utf-8")).hexdigest()
        assert evidence.file_blob_sha == FROZEN_BLOB_SHA
        assert evidence.file_sha256 == hashlib.sha256(
            FROZEN_FILE_TEXT.encode("utf-8")).hexdigest()
        assert evidence.permalink == (
            f"https://github.com/{FROZEN_OWNER}/{FROZEN_REPO}/blob/"
            f"{FROZEN_COMMIT}/{FROZEN_FILE}#L12-L14")
        assert evidence.license_observation.status == "DETECTED"
        assert evidence.license_observation.code_display_allowed is True
        assert evidence.license_observation.files[0].identifier == "MIT"
        assert evidence.verification_status == "VERIFIED"
        assert evidence.provenance_kind == "SOURCE_EXACT"
        assert evidence.verification_checks["public_repository"] == "PASSED"
        assert evidence.verification_checks["commit"] == "PASSED"
        assert evidence.verification_checks["file"] == "PASSED"
        assert evidence.verification_checks["python_symbol"] == "PASSED"
        assert evidence.verification_checks["line_range"] == "PASSED"
        assert evidence.verification_checks["excerpt_hash"] == "PASSED"
        assert evidence.verification_checks["license"] == "PASSED"

    def test_relevance_records_supported_basis(self, verifier):
        query = make_query()
        candidate = make_candidate()
        receipt = run(verifier.verify_specified_public(query, candidate, SCOPE_SHA256))
        assert receipt.evidence.relevance.status == "SUPPORTED"
        basis = receipt.evidence.relevance.basis
        assert any(f"commit:{FROZEN_COMMIT}" in b for b in basis)
        assert any(f"file:{FROZEN_FILE}" in b for b in basis)


class TestVerifyModeAndAuthorization:
    """Authorization boundary: mode, network, allowlist."""

    def test_rejects_wrong_mode(self, verifier):
        query = make_query(source_mode="public_search")
        candidate = make_candidate(source_mode="public_search")
        with pytest.raises(SourceError, match="mode 'public_search'"):
            run(verifier.verify_specified_public(query, candidate, SCOPE_SHA256))

    def test_rejects_no_network(self, verifier):
        query = make_query(network_authorized=False)
        candidate = make_candidate()
        with pytest.raises(SourceError, match="NETWORK_NOT_AUTHORIZED"):
            run(verifier.verify_specified_public(query, candidate, SCOPE_SHA256))

    def test_rejects_empty_allowlist(self, verifier):
        query = make_query(repository_allowlist=[])
        candidate = make_candidate()
        with pytest.raises(SourceError, match="non-empty repository allowlist"):
            run(verifier.verify_specified_public(query, candidate, SCOPE_SHA256))

    def test_rejects_repo_not_in_allowlist(self, verifier):
        query = make_query(repository_allowlist=["other/other"])
        candidate = make_candidate(repository="fastapi/fastapi")
        with pytest.raises(SourceError, match="not in the authorized allowlist"):
            run(verifier.verify_specified_public(query, candidate, SCOPE_SHA256))


class TestVerifyRefAndFile:
    """Ref resolution and file fetching failures."""

    def test_rejects_missing_ref_hint(self, verifier):
        query = make_query()
        candidate = make_candidate(ref_hint=None)
        with pytest.raises(SourceError, match="REF_UNRESOLVED"):
            run(verifier.verify_specified_public(query, candidate, SCOPE_SHA256))

    def test_rejects_unresolvable_ref(self, fake_client_ref_missing):
        verifier = SourceVerifier(fake_client_ref_missing)
        query = make_query()
        candidate = make_candidate(ref_hint="nonexistent-branch")
        with pytest.raises(SourceError, match="REF_UNRESOLVED"):
            run(verifier.verify_specified_public(query, candidate, SCOPE_SHA256))

    def test_rejects_file_not_found(self, fake_client_file_missing):
        verifier = SourceVerifier(fake_client_file_missing)
        query = make_query()
        candidate = make_candidate()
        with pytest.raises(SourceError, match="FILE_NOT_FOUND"):
            run(verifier.verify_specified_public(query, candidate, SCOPE_SHA256))

    def test_rejects_path_escape(self, verifier):
        query = make_query()
        candidate = make_candidate(file_hint="../escape.py")
        with pytest.raises(SourceError, match="repository-relative"):
            run(verifier.verify_specified_public(query, candidate, SCOPE_SHA256))


class TestVerifySymbol:
    """Python AST symbol resolution."""

    def test_rejects_symbol_not_found(self, verifier):
        query = make_query()
        candidate = make_candidate(symbol_hint="nonexistent_function")
        with pytest.raises(SourceError, match="SYMBOL_NOT_FOUND"):
            run(verifier.verify_specified_public(query, candidate, SCOPE_SHA256))

    def test_no_symbol_covers_whole_file(self, verifier):
        query = make_query()
        candidate = make_candidate(symbol_hint=None)
        receipt = run(verifier.verify_specified_public(query, candidate, SCOPE_SHA256))
        evidence = receipt.evidence
        assert evidence.symbol is None
        assert evidence.symbol_kind == "NOT_APPLICABLE"
        assert evidence.verification_checks["python_symbol"] == "NOT_APPLICABLE"
        assert evidence.line_start == 1
        assert evidence.line_end == len(FROZEN_FILE_TEXT.splitlines())

    def test_non_python_file_marks_ast_not_applicable(self, verifier):
        query = make_query()
        candidate = make_candidate(file_hint="README.md", symbol_hint="read_items")
        receipt = run(verifier.verify_specified_public(query, candidate, SCOPE_SHA256))
        evidence = receipt.evidence
        assert evidence.symbol_kind == "NOT_APPLICABLE"
        assert evidence.verification_checks["python_symbol"] == "NOT_APPLICABLE"


class TestVerifyLicense:
    """License detection and code-withholding rules."""

    def test_unknown_license_withholds_code_excerpt(self, fake_client_no_license):
        verifier = SourceVerifier(fake_client_no_license)
        query = make_query()
        candidate = make_candidate()
        receipt = run(verifier.verify_specified_public(query, candidate, SCOPE_SHA256))
        evidence = receipt.evidence
        assert evidence.license_observation.status == "UNKNOWN"
        assert evidence.license_observation.code_display_allowed is False
        assert evidence.code_excerpt == ""
        assert evidence.excerpt_sha256 == hashlib.sha256(b"").hexdigest()
        assert evidence.verification_checks["license"] == "NOT_APPLICABLE"
