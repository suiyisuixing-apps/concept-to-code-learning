"""Full provider tests: build_provider factory, capabilities, dispatch."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from concept_to_code_learning.full_learning.providers import ProviderSettings
from concept_to_code_learning.github_intelligence import build_provider
from concept_to_code_learning.github_intelligence.errors import SourceError
from concept_to_code_learning.github_intelligence.full import GitHubSourceProvider

from .conftest import (
    FROZEN_COMMIT,
    FROZEN_FILE,
    FROZEN_REPO_SLUG,
    make_candidate,
    make_query,
)

SCOPE_SHA256 = "a" * 64


def run(coro):
    return asyncio.run(coro)


@pytest.fixture
def settings(tmp_path: Path) -> ProviderSettings:
    return ProviderSettings(root=tmp_path, data_dir=tmp_path / "data",
                            github_token="test-token-not-real")


@pytest.fixture
def provider(settings: ProviderSettings) -> GitHubSourceProvider:
    result = build_provider(settings)
    assert isinstance(result, GitHubSourceProvider)
    return result


class TestBuildProvider:
    def test_returns_source_provider(self, settings):
        result = build_provider(settings)
        assert isinstance(result, GitHubSourceProvider)
        assert result.PROVIDER_ID == "github-intelligence"


class TestCapabilities:
    def test_reports_implemented_and_available(self, provider):
        caps = run(provider.capabilities())
        assert caps.provider_id == "github-intelligence"
        assert caps.implemented is True
        assert caps.available is True
        assert caps.mode == "LIVE"
        assert caps.status == "AVAILABLE"

    def test_features_list_specified_public(self, provider):
        caps = run(provider.capabilities())
        assert any("specified_public" in f for f in caps.features)

    def test_data_flow_describes_verify_pipeline(self, provider):
        caps = run(provider.capabilities())
        joined = " ".join(caps.data_flow)
        assert "commit" in joined
        assert "license" in joined


class TestLocalHandles:
    def test_returns_empty_without_authorized_roots(self, settings):
        provider = build_provider(settings)
        assert run(provider.local_handles()) == []

    def test_returns_authorized_roots(self, tmp_path: Path):
        root = tmp_path / "repo"
        root.mkdir()
        settings = ProviderSettings(root=tmp_path, data_dir=tmp_path / "data",
                                    authorized_local_roots=(root,))
        provider = build_provider(settings)
        handles = run(provider.local_handles())
        assert str(root.resolve()) in handles


class TestSearchDispatch:
    def test_specified_public_dispatches_to_searcher(self, provider):
        query = make_query(repository_allowlist=[FROZEN_REPO_SLUG])
        result = run(provider.search(query))
        assert result.query_id == query.query_id
        assert len(result.candidates) == 1

    def test_public_search_raises_not_implemented(self, provider):
        query = make_query(source_mode="public_search",
                           repository_allowlist=[FROZEN_REPO_SLUG])
        with pytest.raises(SourceError, match="NOT_IMPLEMENTED"):
            run(provider.search(query))

    def test_local_authorized_raises_not_implemented(self, provider):
        query = make_query(source_mode="local_authorized",
                           repository_allowlist=[])
        with pytest.raises(SourceError, match="NOT_IMPLEMENTED"):
            run(provider.search(query))


class TestVerifyDispatch:
    def test_specified_public_dispatches_to_verifier(self, provider, monkeypatch):
        # Dispatch test: replace the verifier with a stub so no network is used.
        async def stub_verify(query, candidate, scope_sha256):
            from concept_to_code_learning.full_learning.ports import VerificationReceipt
            return VerificationReceipt(query_id=query.query_id,
                                        candidate_id=candidate.candidate_id,
                                        scope_sha256=scope_sha256, evidence=None)
        monkeypatch.setattr(provider._verifier, "verify_specified_public", stub_verify)
        query = make_query(repository_allowlist=[FROZEN_REPO_SLUG])
        candidate = make_candidate(repository=FROZEN_REPO_SLUG,
                                   ref_hint=FROZEN_COMMIT,
                                   file_hint=FROZEN_FILE)
        receipt = run(provider.verify(query, candidate, SCOPE_SHA256))
        assert receipt.query_id == query.query_id

    def test_public_search_verify_raises_not_implemented(self, provider):
        query = make_query(source_mode="public_search",
                           repository_allowlist=[FROZEN_REPO_SLUG])
        candidate = make_candidate(source_mode="public_search")
        with pytest.raises(SourceError, match="NOT_IMPLEMENTED"):
            run(provider.verify(query, candidate, SCOPE_SHA256))

    def test_local_authorized_verify_raises_not_implemented(self, provider):
        query = make_query(source_mode="local_authorized",
                           repository_allowlist=[])
        candidate = make_candidate(source_mode="local_authorized")
        with pytest.raises(SourceError, match="NOT_IMPLEMENTED"):
            run(provider.verify(query, candidate, SCOPE_SHA256))


class TestClose:
    def test_close_does_not_raise(self, provider):
        run(provider.close())  # Should not raise.
