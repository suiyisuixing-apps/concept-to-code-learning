"""AI suggestions are untrusted hints; only actual GitHub responses define sources."""

import asyncio

import httpx

from concept_to_code_learning.github_intelligence.errors import SourceError
from concept_to_code_learning.github_intelligence.github_client import GitHubRawClient
from concept_to_code_learning.github_intelligence.specifier import SpecifiedPublicSearcher

from .conftest import FROZEN_FILE, FROZEN_REPO_SLUG, FakeGitHubRawClient, make_query


def test_stale_ai_repository_falls_back_to_actual_public_search():
    class Client(FakeGitHubRawClient):
        async def repository(self, owner, name):
            if owner == "missing":
                raise SourceError("FILE_NOT_FOUND", "repository", "Missing suggestion", 404)
            return await super().repository(owner, name)
    client = Client()
    query = make_query(source_mode="public_search", repository_allowlist=[],
                       concept_terms=["dependency"]).model_copy(update={"auto_public_search": True,
                       "query_terms_approved": True, "approved_query_terms": ["dependency"],
                       "repository_hints": ["missing/library", "missing/other", "missing/third"], "file_hints": ["invented.py", "../../outside.py"]})
    result = asyncio.run(SpecifiedPublicSearcher(client).search(query))
    assert result.candidates[0].repository == FROZEN_REPO_SLUG
    assert result.candidates[0].file_hint == FROZEN_FILE


def test_ai_hints_never_expand_a_specified_repository():
    client = FakeGitHubRawClient()
    query = make_query(repository_allowlist=[FROZEN_REPO_SLUG]).model_copy(
        update={"repository_hints": ["unrelated/repo"]})
    result = asyncio.run(SpecifiedPublicSearcher(client).search(query))
    assert {c.repository for c in result.candidates} == {FROZEN_REPO_SLUG}


def test_repository_search_uses_topic_then_alternative_instead_of_all_symbols():
    async def scenario():
        queries = []
        def handler(request):
            queries.append(request.url.params["q"])
            items = [] if len(queries) == 1 else [{"full_name": "actual/library", "private": False}]
            return httpx.Response(200, json={"items": items})
        client = GitHubRawClient(transport=httpx.MockTransport(handler))
        try:
            found = await client.search_repositories(["mutual information", "entropy", "fit"], 3)
        finally:
            await client.close()
        assert found == ["actual/library"]
        assert len(queries) == 2 and '"mutual information"' in queries[0]
        assert '"entropy"' not in queries[0] and '"fit"' not in queries[0]
        assert "in:name,description,readme" in queries[0]
    asyncio.run(scenario())


def test_oversized_automatic_candidate_uses_an_inspectable_alternative():
    class Client(FakeGitHubRawClient):
        async def tree(self, owner, name, commit):
            if owner == "large":
                raise SourceError("INVALID_PROVIDER_RESPONSE", "tree", "Oversized tree", 413)
            return await super().tree(owner, name, commit)
    query = make_query(source_mode="public_search", repository_allowlist=[],
                       concept_terms=["dependency"]).model_copy(update={"auto_public_search": True,
                       "query_terms_approved": True, "approved_query_terms": ["dependency"],
                       "repository_hints": ["large/library"]})
    result = asyncio.run(SpecifiedPublicSearcher(Client()).search(query))
    assert result.candidates[0].repository == FROZEN_REPO_SLUG


def test_algorithm_name_outranks_generic_graph_and_path_terms():
    from concept_to_code_learning.github_intelligence.discovery import ranked_paths
    paths = ["src/algorithms/graph/eulerian-path/eulerianPath.js",
             "src/algorithms/graph/eulerian-path/__test__/eulerianPath.test.js",
             "src/algorithms/graph/dijkstra/dijkstra.js",
             "src/algorithms/graph/dijkstra/__test__/dijkstra.test.js",
             "src/data-structures/priority-queue/PriorityQueue.js"]
    ordered = ranked_paths(paths, ["shortest path", "dijkstra algorithm", "priority queue", "weighted graph"])
    assert ordered[0] == "src/algorithms/graph/dijkstra/dijkstra.js"


def test_excerpts_ending_in_a_blank_line_keep_the_exact_inclusive_range():
    from concept_to_code_learning.github_intelligence.verifier import excerpt
    lines = ["prediction = 1"] + [f"value_{i} = {i}" for i in range(1, 35)] + [""] + ["later = 1"] * 10
    _, start, end, code = excerpt("\n".join(lines), "example.py", None, ["prediction"])
    assert len(code.splitlines()) == end - start + 1
    assert code == "\n".join(lines[start - 1:end]) and end == 35


def test_partial_graph_word_does_not_claim_a_shortest_path_match():
    from concept_to_code_learning.github_intelligence.discovery import matched
    assert matched("class CloneGraph { HashMap map; cloneGraph(node); }", ["weighted graph", "priority queue"]) == []
    assert matched("class Dijkstra { PriorityQueue queue; }", ["dijkstra", "priority queue"]) == ["dijkstra", "priority queue"]
    assert matched("benefit office", ["fit"]) == []
    assert matched("loss.backward()", ["loss.backward"]) == ["loss.backward"]
