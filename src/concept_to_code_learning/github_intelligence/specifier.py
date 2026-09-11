"""specified_public mode: discover candidates from an authorized allowlist.

The current slice returns framework candidates (repo + matched terms) without
performing concept-term retrieval across the repository contents. Real code
discovery (PR #67 section C3) is tracked in HANDOFF.md as the next slice; the
verify path is fully implemented and tested offline with a frozen commit.
"""

from __future__ import annotations

from concept_to_code_learning.full_contracts.models import (
    SearchCandidate,
    SearchResult,
    SourceQuery,
    uid,
    utcnow,
)

from .errors import SourceError
from .github_client import GitHubRawClient


class SpecifiedPublicSearcher:
    """Discovers allowlist-bound candidates for specified_public mode."""

    def __init__(self, client: GitHubRawClient):
        # Client is kept for the future C3 retrieval slice; today's search is
        # allowlist-only and does not fetch repository contents.
        self._client = client

    async def search(self, query: SourceQuery) -> SearchResult:
        self._require_mode(query, "specified_public")
        self._require_network(query)
        self._require_allowlist(query)
        candidates = [self._framework_candidate(query, repo, query.concept_terms)
                      for repo in query.repository_allowlist]
        return SearchResult(
            mode="LIVE",
            query_id=query.query_id,
            candidates=candidates,
            selection_required=True,
            status="NEEDS_CONFIRMATION",
            warnings=[
                "Concept-term retrieval (C3) is not implemented in this slice; "
                "candidates are framework entries from the allowlist.",
                "Provide ref_hint, file_hint and symbol_hint during selection "
                "so the verifier can pin a commit and locate the symbol.",
            ],
        )

    def _framework_candidate(
        self, query: SourceQuery, repo: str, matched_terms: list[str],
    ) -> SearchCandidate:
        return SearchCandidate(
            mode="LIVE",
            candidate_id=uid(),
            query_id=query.query_id,
            source_mode="specified_public",
            repository=repo,
            local_handle=None,
            ref_hint=None,
            file_hint=None,
            symbol_hint=None,
            matched_terms=list(matched_terms),
            ranking_reason=("Allowlisted repository; awaiting user-selected "
                            "ref, file and symbol."),
            discovery_method="allowlist_framework",
            discovery_status="NEEDS_CONFIRMATION",
            retrieved_at=utcnow(),
        )

    def _require_mode(self, query: SourceQuery, expected: str) -> None:
        if query.source_mode != expected:
            raise SourceError("INVALID_PROVIDER_RESPONSE", "search",
                              f"Searcher received mode {query.source_mode!r}, expected {expected!r}",
                              status=422)

    def _require_network(self, query: SourceQuery) -> None:
        if not query.network_authorized:
            raise SourceError("NETWORK_NOT_AUTHORIZED", "search",
                              "specified_public search requires explicit network authorization",
                              status=403, needed_action="Set network_authorized=true with user consent.")

    def _require_allowlist(self, query: SourceQuery) -> None:
        if not query.repository_allowlist:
            raise SourceError("NETWORK_NOT_AUTHORIZED", "search",
                              "specified_public search requires a non-empty repository allowlist",
                              status=403, needed_action="Provide at least one owner/repo in the allowlist.")
