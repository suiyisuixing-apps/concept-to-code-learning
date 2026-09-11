"""Specified_public search tests: framework candidates and authorization."""

from __future__ import annotations

import asyncio

import pytest

from concept_to_code_learning.github_intelligence.errors import SourceError
from concept_to_code_learning.github_intelligence.specifier import SpecifiedPublicSearcher

from .conftest import FROZEN_REPO_SLUG, make_query


def run(coro):
    return asyncio.run(coro)


@pytest.fixture
def searcher(fake_client) -> SpecifiedPublicSearcher:
    return SpecifiedPublicSearcher(fake_client)


class TestSearchHappyPath:
    def test_discovers_real_file_and_symbol_from_allowlist(self, searcher):
        query = make_query(repository_allowlist=[FROZEN_REPO_SLUG])
        result = run(searcher.search(query))
        assert result.query_id == query.query_id
        assert len(result.candidates) == 1
        assert result.candidates[0].repository == FROZEN_REPO_SLUG
        assert result.candidates[0].source_mode == "specified_public"
        assert result.candidates[0].discovery_status == "CANDIDATE"
        assert result.candidates[0].discovery_method == "bounded_tree_and_static_text"
        assert result.selection_required is False
        assert result.status == "CANDIDATES"

    def test_normal_query_needs_no_manual_file_or_symbol(self, searcher):
        query = make_query()
        result = run(searcher.search(query))
        assert result.candidates[0].file_hint
        assert result.candidates[0].ref_hint
        assert result.candidates[0].symbol_hint
        assert not result.warnings

    def test_matched_terms_report_only_complete_text_matches(self, searcher):
        query = make_query(concept_terms=["dependency injection", "Depends"])
        result = run(searcher.search(query))
        # This fixture contains Depends and "dependency", but not "injection".
        assert result.candidates[0].matched_terms == ["Depends"]


class TestSearchAuthorization:
    def test_rejects_wrong_mode(self, searcher):
        query = make_query(source_mode="public_search")
        with pytest.raises(SourceError, match="QUERY_TERMS_NOT_APPROVED"):
            run(searcher.search(query))

    def test_rejects_no_network(self, searcher):
        query = make_query(network_authorized=False)
        with pytest.raises(SourceError, match="NETWORK_NOT_AUTHORIZED"):
            run(searcher.search(query))

    def test_rejects_empty_allowlist(self, searcher):
        query = make_query(repository_allowlist=[])
        with pytest.raises(SourceError, match="NO_RELEVANT_SOURCE"):
            run(searcher.search(query))
