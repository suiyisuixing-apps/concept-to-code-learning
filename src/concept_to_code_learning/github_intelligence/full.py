"""Member entrypoint installed by the Lead in full_learning/providers.py.

The factory is a synchronous local constructor that returns a SourceProvider
whose methods are async. It never performs network work during construction;
the first network call happens only when an authorized verify() runs.
"""

from __future__ import annotations

from concept_to_code_learning.full_contracts.models import (
    ProviderCapability,
    SearchCandidate,
    SearchResult,
    SourceQuery,
)
from concept_to_code_learning.full_learning.io import run_io
from concept_to_code_learning.full_learning.ports import (
    SourceProvider,
    VerificationReceipt,
)
from concept_to_code_learning.full_learning.providers import ProviderSettings

from .errors import SourceError
from .github_client import GitHubRawClient
from .local import LocalSources
from .registry import LocalRegistry
from .specifier import SpecifiedPublicSearcher
from .verifier import SourceVerifier


def build_provider(settings: ProviderSettings) -> SourceProvider:
    """Construct the GitHub source provider from Lead-supplied settings."""
    client = GitHubRawClient(token=settings.github_token,
                             cache_dir=settings.data_dir / "public-source-cache")
    verifier = SourceVerifier(client)
    searcher = SpecifiedPublicSearcher(client)
    registry = LocalRegistry(settings.authorized_local_roots)
    return GitHubSourceProvider(client=client, verifier=verifier,
                                searcher=searcher, registry=registry)


class GitHubSourceProvider(SourceProvider):
    """Public and authorized-local static evidence provider."""

    PROVIDER_ID = "github-intelligence"

    def __init__(self, *, client: GitHubRawClient, verifier: SourceVerifier,
                 searcher: SpecifiedPublicSearcher, registry: LocalRegistry):
        self._client = client
        self._verifier = verifier
        self._searcher = searcher
        self._registry = registry
        self._local = LocalSources(registry)

    async def capabilities(self) -> ProviderCapability:
        local = bool(await self.local_handles())
        public, reason = self._client.network_health()
        return ProviderCapability(
            provider_id=self.PROVIDER_ID,
            implemented=True,
            available=local or public,
            mode="LIVE",
            features=[
                "specified_public: bounded concept discovery",
                "specified_public.verify (commit, file, AST, hash, license)",
                "public_search: context-derived public technical concepts",
            ] + (["local_authorized: tracked files, hashes and dirty state"] if local else []),
            status="AVAILABLE" if local or public else "UNAVAILABLE",
            reason_code=reason,
            needed_action=("选择公开仓库后检查连接。" if reason == "GITHUB_NOT_CHECKED"
                           else "检查 GitHub 连接或配置授权的本地仓库。" if not public else None),
            data_flow=[
                "search: authorized scope → file tree → concept matching → static symbols",
                "verify: ref→commit → raw bytes → static AST → SHA256 → license → CodeEvidence",
                "local_handles: host-configured roots; no web path endpoint",
            ],
        )

    async def search(self, query: SourceQuery) -> SearchResult:
        if query.source_mode in {"specified_public", "public_search"}:
            return await self._searcher.search(query)
        if query.source_mode == "local_authorized":
            return await self._local.search(query)
        raise SourceError("INVALID_PROVIDER_RESPONSE", "search",
                          f"Unknown source_mode: {query.source_mode!r}", status=422)

    async def verify(self, query: SourceQuery, candidate: SearchCandidate,
                     scope_sha256: str) -> VerificationReceipt:
        if query.source_mode in {"specified_public", "public_search"}:
            return await self._verifier.verify_specified_public(
                query, candidate, scope_sha256)
        if query.source_mode == "local_authorized":
            return await self._local.verify(query, candidate, scope_sha256)
        raise SourceError("INVALID_PROVIDER_RESPONSE", "verify",
                          f"Unknown source_mode: {query.source_mode!r}", status=422)

    async def local_handles(self) -> list[str]:
        # INTERFACES.md: handles are host-configured, never accepted from HTTP.
        return await run_io(self._registry.handles)

    async def close(self) -> None:
        await self._client.close()
