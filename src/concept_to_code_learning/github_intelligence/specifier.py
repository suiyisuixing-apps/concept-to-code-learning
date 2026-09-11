"""Discover file paths and symbols within the authorized public repository scope."""

import asyncio

from concept_to_code_learning.learning_concepts import guide_for_terms

from .discovery import candidate, ranked_paths, result
from .errors import SourceError


class SpecifiedPublicSearcher:
    def __init__(self, client):
        self._client = client

    async def search(self, query):
        if not query.network_authorized:
            raise SourceError("NETWORK_NOT_AUTHORIZED", "search", "尚未授权 GitHub 联网。", 403)
        repositories = query.repository_allowlist[:query.scope_limit.repositories]
        guide = guide_for_terms(query.concept_terms)
        if query.source_mode == "specified_public" and not repositories:
            raise SourceError("NO_RELEVANT_SOURCE", "search", "未指定公开仓库。", 422)
        if query.source_mode == "public_search":
            if (not query.query_terms_approved or not set(t.casefold() for t in query.concept_terms)
                    <= set(t.casefold() for t in query.approved_query_terms)):
                raise SourceError("QUERY_TERMS_NOT_APPROVED", "search", "公开搜索词尚未获得逐项确认。", 403)
            if query.auto_public_search and guide:
                repositories = list(guide.repositories[:query.scope_limit.repositories])
            else:
                repositories = await self._client.search_repositories(query.concept_terms,
                                                query.scope_limit.repositories, query.language_hint)
        candidates, warnings, reads = [], [], 0
        for i, repo in enumerate(repositories):
            owner, name = repo.split("/", 1)
            meta = await self._client.repository(owner, name)
            commit = await self._client.resolve_ref(owner, name, meta["default_branch"])
            tree = await self._client.tree(owner, name, commit)
            if tree.get("truncated"):
                warnings.append("仓库文件树被 GitHub 截断；本次只检索已返回的部分。")
            paths = [x["path"] for x in tree.get("tree", []) if x.get("type") == "blob"
                     and x.get("mode") in {"100644", "100755"} and 0 < x.get("size", 0) <= 1024*1024]
            remaining = query.scope_limit.files - reads
            budget = max(1, remaining // (len(repositories)-i)) if remaining > 0 else 0
            ranked = ranked_paths(paths, query.concept_terms, query.language_hint)
            hints = [p for p in (guide.paths if guide and repo in guide.repositories else ()) if p in ranked]
            selected = (hints or ranked[:max(2, query.max_sources * 2)])[:budget]
            # Read a bounded batch together; verification still checks each exact blob.
            batch = await asyncio.gather(*(self._client.fetch_raw(owner, name, commit, path)
                                           for path in selected))
            for path, raw in zip(selected, batch, strict=True):
                reads += 1
                try:
                    text = raw.decode("utf-8")
                except UnicodeError:
                    warnings.append("一个非 UTF-8 源码文件未用于讲解。")
                    continue
                value = candidate(query, repo, None, commit, path, text)
                if value:
                    candidates.append(value)
        candidates.sort(key=lambda c: (not (guide and c.file_hint in guide.paths
                                           and c.file_hint.startswith("examples/")), -len(c.matched_terms)))
        # Interleave repositories so a comparison can choose independent implementations.
        unique, rest, seen = [], [], set()
        for value in candidates:
            if value.repository in seen:
                rest.append(value)
            else:
                unique.append(value)
                seen.add(value.repository)
        return result(query, unique + rest, warnings)
