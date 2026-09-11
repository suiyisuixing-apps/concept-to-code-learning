"""Public cache and quota behavior use synthetic HTTP responses, never account credentials."""

import asyncio
import base64
import json
import time

import httpx
import pytest

from concept_to_code_learning.github_intelligence.errors import SourceError
from concept_to_code_learning.github_intelligence.github_client import GitHubRawClient
from concept_to_code_learning.github_intelligence.public_cache import PublicResponseCache

COMMIT = "a" * 40


def test_restart_reuses_pinned_public_bytes_but_rechecks_visibility(tmp_path):
    async def scenario():
        seen, private = [], False
        def handler(request):
            seen.append(request.url.path)
            if "/contents/" in request.url.path:
                return httpx.Response(200, json={"type": "file", "encoding": "base64",
                    "content": base64.b64encode(b"print('public')\n").decode(), "sha": "b" * 40})
            return httpx.Response(200, json={"private": private, "full_name": "sample/library"})
        def client():
            return GitHubRawClient(token="fixture-secret", cache_dir=tmp_path,
                                   transport=httpx.MockTransport(handler))
        first = client()
        await first.repository("sample", "library")
        assert await first.fetch_raw("sample", "library", COMMIT, "example.py") == b"print('public')\n"
        await first.close()
        assert len(seen) == 2
        persisted = list(tmp_path.glob("*.json"))
        assert len(persisted) == 1 and "fixture-secret" not in persisted[0].read_text(encoding="utf-8")
        second = client()
        await second.repository("sample", "library")
        assert await second.fetch_raw("sample", "library", COMMIT, "example.py") == b"print('public')\n"
        await second.close()
        assert len(seen) == 3 and seen[-1] == "/repos/sample/library"
        private = True
        third = client()
        with pytest.raises(SourceError, match="REPO_UNAVAILABLE"):
            await third.repository("sample", "library")
        await third.close()
        assert len(list(tmp_path.glob("*.json"))) == 1
    asyncio.run(scenario())


def test_unverified_public_status_does_not_persist_source_bytes(tmp_path):
    async def scenario():
        client = GitHubRawClient(cache_dir=tmp_path, transport=httpx.MockTransport(lambda _: httpx.Response(
            200, json={"type": "file", "encoding": "base64", "content": "c291cmNl", "sha": "b" * 40})))
        await client.fetch_raw("sample", "library", COMMIT, "example.py")
        await client.close()
        assert not list(tmp_path.iterdir())
    asyncio.run(scenario())


def test_public_cache_rejects_corruption_expiration_and_evicts_old_entries(tmp_path):
    cache = PublicResponseCache(tmp_path)
    cache.put("first", b"source")
    path = next(tmp_path.glob("*.json"))
    value = json.loads(path.read_text(encoding="utf-8"))
    value["body"] = base64.b64encode(b"changed source").decode()
    path.write_text(json.dumps(value), encoding="utf-8")
    assert cache.get("first") is None
    cache.put("first", b"source")
    value = json.loads(path.read_text(encoding="utf-8"))
    value["expires"] = time.time() - 1
    path.write_text(json.dumps(value), encoding="utf-8")
    assert cache.get("first") is None
    cache.max_entries = 2
    cache.put("second", b"source2")
    cache.put("third", b"source3")
    assert len(list(tmp_path.glob("*.json"))) == 2
    assert cache.get("second") == b"source2" and cache.get("third") == b"source3"


@pytest.mark.parametrize("primary", [True, False])
def test_primary_quotas_are_independent_but_secondary_limits_apply_globally(primary):
    async def scenario():
        seen = []
        def handler(request):
            seen.append(request.url.path)
            if request.url.path.startswith("/search/"):
                return httpx.Response(200, json={"items": [{"private": False, "full_name": "sample/library"}]})
            return httpx.Response(403, headers={"retry-after": "60",
                                  "x-ratelimit-remaining": "0" if primary else "50"})
        client = GitHubRawClient(transport=httpx.MockTransport(handler))
        with pytest.raises(SourceError, match="RATE_LIMITED"):
            await client.repository("sample", "library")
        with pytest.raises(SourceError, match="RATE_LIMITED"):
            await client.repository("sample", "another")
        if primary:
            assert await client.search_repositories(["dijkstra"], 1) == ["sample/library"]
        else:
            with pytest.raises(SourceError, match="RATE_LIMITED"):
                await client.search_repositories(["dijkstra"], 1)
        assert len(seen) == (2 if primary else 1)
        await client.close()
    asyncio.run(scenario())
