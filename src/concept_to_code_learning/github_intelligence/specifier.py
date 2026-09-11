"""Discover actual files from AI hints and bounded public search, never execution."""

import asyncio
from pathlib import PurePosixPath

from concept_to_code_learning.learning_concepts import guide_for, guide_for_terms

from .discovery import candidate, ranked_paths, result
from .errors import SourceError


class SpecifiedPublicSearcher:
    def __init__(self, client):
        self._client = client

    async def search(self, query):
        if not query.network_authorized:
            raise SourceError("NETWORK_NOT_AUTHORIZED", "search", "尚未授权 GitHub 联网。", 403)
        automatic = query.source_mode == "public_search" and query.auto_public_search
        guide = guide_for_terms(query.concept_terms) or guide_for(" ".join(query.concept_terms))
        repositories = query.repository_allowlist[:query.scope_limit.repositories]
        if query.source_mode == "specified_public" and not repositories:
            raise SourceError("NO_RELEVANT_SOURCE", "search", "未指定公开仓库。", 422)
        if query.source_mode == "public_search":
            if (not query.query_terms_approved or not set(t.casefold() for t in query.concept_terms)
                    <= set(t.casefold() for t in query.approved_query_terms)):
                raise SourceError("QUERY_TERMS_NOT_APPROVED", "search", "公开搜索词尚未获得逐项确认。", 403)
            repositories = list(dict.fromkeys(list(guide.repositories if guide else ()) +
                                              query.repository_hints)) if automatic else []

        candidates, warnings, visited, inspected, reads = [], [], set(), set(), 0

        async def inspect(repo):
            nonlocal reads
            if repo in visited or len(inspected) >= query.scope_limit.repositories:
                return
            visited.add(repo)
            owner, name = repo.split("/", 1)
            try:
                meta = await self._client.repository(owner, name)
                commit = await self._client.resolve_ref(owner, name, meta["default_branch"])
                tree = await self._client.tree(owner, name, commit)
            except SourceError as exc:
                # AI repository suggestions have no authority. A stale suggestion
                # is skipped; actual network/authentication failures remain visible.
                if automatic and (exc.code == "FILE_NOT_FOUND" or
                                  exc.code == "REPO_UNAVAILABLE" and exc.status == 403
                                  or exc.stage == "tree" and exc.status == 413):
                    return
                raise
            if automatic and tree.get("truncated"):
                return  # Find an inspectable alternative rather than an unlicensable partial tree.
            inspected.add(repo)
            if tree.get("truncated"):
                warnings.append("仓库文件树被 GitHub 截断；本次只检索已返回的部分。")
            paths = [x["path"] for x in tree.get("tree", []) if x.get("type") == "blob"
                     and x.get("mode") in {"100644", "100755"} and 0 < x.get("size", 0) <= 1024*1024]
            # A remembered basename can locate an implementation even when its
            # actual repository directory or language differs from the AI hint.
            hint_names = [PurePosixPath(path).stem for path in query.file_hints]
            ranked = ranked_paths(paths, hint_names + query.concept_terms, query.language_hint)
            guide_paths = guide.paths if guide and repo in guide.repositories else ()
            # Every path hint must exist in the returned tree before it can be read.
            hints = [p for p in dict.fromkeys([*guide_paths, *query.file_hints]) if p in ranked]
            remaining = query.scope_limit.files - reads
            budget = min(remaining, max(2, query.max_sources * 2))
            selected = list(dict.fromkeys(hints + ranked))[:budget]
            batch = await asyncio.gather(*(self._client.fetch_raw(owner, name, commit, path)
                                           for path in selected), return_exceptions=True)
            for path, raw in zip(selected, batch, strict=True):
                reads += 1
                if isinstance(raw, BaseException):
                    if isinstance(raw, SourceError) and raw.code == "FILE_NOT_FOUND":
                        continue
                    raise raw
                try:
                    text = raw.decode("utf-8")
                except UnicodeError:
                    warnings.append("一个非 UTF-8 源码文件未用于讲解。")
                    continue
                value = candidate(query, repo, None, commit, path, text)
                if value:
                    candidates.append(value)

        def enough():
            return (len(candidates) >= query.max_sources and
                    len({c.repository for c in candidates}) >= min(query.max_sources, 2))

        for repo in repositories[:query.scope_limit.repositories]:
            await inspect(repo)
            if enough() or reads >= query.scope_limit.files:
                break
        if (query.source_mode == "public_search" and not enough() and reads < query.scope_limit.files
                and len(inspected) < query.scope_limit.repositories):
            discovered = await self._client.search_repositories(query.concept_terms,
                                            query.scope_limit.repositories, query.language_hint)
            for repo in discovered:
                await inspect(repo)
                if enough() or reads >= query.scope_limit.files:
                    break
        candidates.sort(key=lambda c: (not (c.file_hint.startswith("examples/") or
                                           c.file_hint in query.file_hints), -len(c.matched_terms)))
        unique, rest, seen = [], [], set()
        for value in candidates:
            if value.repository in seen:
                rest.append(value)
            else:
                unique.append(value)
                seen.add(value.repository)
        return result(query, unique + rest, warnings)
