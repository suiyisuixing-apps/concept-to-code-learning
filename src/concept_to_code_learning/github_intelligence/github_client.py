"""Bounded, cancellable public GitHub reads with public-only caching and no ambient proxy."""

import asyncio
import base64
import json
import re
import time
from collections import OrderedDict
from urllib.parse import quote, urlencode, urlsplit

import httpx

from concept_to_code_learning.full_learning.io import run_io

from .errors import SourceError
from .public_cache import PublicResponseCache

ALLOWED_HOSTS = frozenset({"raw.githubusercontent.com", "api.github.com"})
MAX_BODY_BYTES = 1024 * 1024


def safe_path(path):
    if (
        not isinstance(path, str)
        or not path
        or len(path) > 1000
        or path.startswith("/")
        or "\\" in path
        or "\x00" in path
        or any(p in {".", "..", ""} for p in path.split("/"))
    ):
        raise SourceError("FILE_NOT_FOUND", "sources", "源码路径不合法。", 422)
    return quote(path, safe="/")


def repo_path(owner, name):
    if not all(re.fullmatch(r"[A-Za-z0-9_-][A-Za-z0-9_.-]*", s or "") for s in (owner, name)):
        raise SourceError("REPO_UNAVAILABLE", "sources", "仓库标识不合法。", 422)
    return f"https://api.github.com/repos/{owner}/{name}"


class GitHubRawClient:
    def __init__(self, *, token=None, timeout=10.0, retries=1, transport=None, cache_dir=None):
        self._token = token
        self._timeout = min(30, max(0.1, timeout))
        self._retries = min(1, max(0, retries))
        self._client = None
        self._transport = transport
        self._cache = OrderedDict()
        self._cache_size = 0
        self._blocked_until = {}
        self._public_repositories = set()
        self._public_cache = PublicResponseCache(cache_dir)
        self._network_observation = None

    def network_health(self):
        if self._network_observation is None or time.monotonic() - self._network_observation[0] > 60:
            return False, "GITHUB_NOT_CHECKED"
        return self._network_observation[1:]

    async def _ensure_client(self):
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=self._timeout,
                follow_redirects=False,
                trust_env=False,
                transport=self._transport,
            )
        return self._client

    async def repository(self, owner, name):
        data = await self._get_json(repo_path(owner, name), stage="repository")
        if (
            data.get("private") is not False
            or data.get("visibility", "public") != "public"
            or str(data.get("full_name", "")).casefold() != f"{owner}/{name}".casefold()
        ):
            raise SourceError("REPO_UNAVAILABLE", "repository", "只允许已核实的公开仓库。", 403)
        self._public_repositories.add(f"{owner}/{name}".casefold())
        return data

    async def search_repositories(self, terms, limit, language=None):
        # A concept and its implementation symbols are alternatives, not mandatory
        # AND conditions on repository descriptions. Try the primary topic first.
        topics = list(dict.fromkeys(re.sub(r"\b(?:implementation|implementations|examples?|tutorials?)\b",
                                          "", term, flags=re.I).strip() for term in terms[:2]))
        for term in topics:
            if not term:
                continue
            word = re.sub(r'["\\\x00-\x1f]', " ", term)
            query = '"' + word + '" in:name,description,readme is:public'
            if language and re.fullmatch(r"[A-Za-z0-9+#._-]{1,30}", language):
                query += " language:" + language
            url = "https://api.github.com/search/repositories?" + urlencode(
                {"q": query, "per_page": min(20, limit), "sort": "stars"})
            data = await self._get_json(url, stage="search")
            found = [r["full_name"] for r in data.get("items", []) if isinstance(r, dict)
                     and r.get("private") is False and isinstance(r.get("full_name"), str)
                     and re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", r["full_name"])]
            if found:
                return found[:limit]
        return []

    async def tree(self, owner, name, commit, *, recursive=True):
        return await self._get_json(
            repo_path(owner, name) + f"/git/trees/{quote(commit, safe='')}"
            + ("?recursive=1" if recursive else ""),
            stage="tree",
        )

    async def fetch_raw(self, owner, name, commit, path):
        if not re.fullmatch(r"[0-9a-f]{40}", commit):
            raise SourceError("REF_UNRESOLVED", "fetch", "源码读取必须固定 Commit。", 422)
        # The contents API returns bytes and blob identity together and avoids reliance
        # on a separate raw-content host, which is unavailable on some networks.
        data = await self._get_json(
            repo_path(owner, name)
            + "/contents/"
            + safe_path(path)
            + "?"
            + urlencode({"ref": commit}),
            stage="contents",
        )
        if data.get("type") != "file" or data.get("encoding") != "base64":
            raise SourceError("FILE_NOT_FOUND", "fetch", "路径不是支持大小的普通源码文件。", 422)
        try:
            raw = base64.b64decode("".join(data["content"].split()), validate=True)
        except (ValueError, KeyError, TypeError):
            raise SourceError(
                "INVALID_PROVIDER_RESPONSE", "fetch", "源码字节编码无效。", 502
            ) from None
        if len(raw) > MAX_BODY_BYTES:
            raise SourceError(
                "INVALID_PROVIDER_RESPONSE", "fetch", "源码文件超过 1 MiB 上限。", 413
            )
        return raw

    async def resolve_ref(self, owner, name, ref):
        data = await self._get_json(
            repo_path(owner, name) + "/commits/" + quote(ref, safe=""), stage="commit"
        )
        sha = data.get("sha")
        if not isinstance(sha, str) or not re.fullmatch(r"[a-f0-9]{40}", sha):
            raise SourceError("REF_UNRESOLVED", "commit", "未得到有效的固定 Commit。", 502)
        return sha

    async def fetch_blob_sha(self, owner, name, commit, path):
        data = await self._get_json(
            repo_path(owner, name)
            + "/contents/"
            + safe_path(path)
            + "?"
            + urlencode({"ref": commit}),
            stage="blob",
        )
        if data.get("type") != "file":
            raise SourceError("FILE_NOT_FOUND", "blob", "路径不是普通源码文件。", 422)
        return data.get("sha")

    async def fetch_license(self, owner, name, commit, path):
        try:
            return await self.fetch_raw(owner, name, commit, path)
        except SourceError as exc:
            if exc.code == "FILE_NOT_FOUND":
                return None
            raise

    async def _get_bytes(self, url, *, stage, allow_404=False):
        response = await self._request("GET", url, stage=stage, allow_404=allow_404)
        return response.content

    async def _get_json(self, url, *, stage):
        response = await self._request("GET", url, stage=stage)
        try:
            data = json.loads(response.content)
            if not isinstance(data, dict):
                raise ValueError
            return data
        except (ValueError, UnicodeError):
            raise SourceError(
                "INVALID_PROVIDER_RESPONSE", stage, "GitHub 返回的数据格式无效。", 502
            ) from None

    async def _request(self, method, url, *, stage, allow_404=False, accept=None):
        parts = urlsplit(url)
        if (
            parts.scheme != "https"
            or parts.hostname not in ALLOWED_HOSTS
            or parts.username
            or parts.password
        ):
            raise SourceError("NETWORK_NOT_AUTHORIZED", stage, "地址超出 GitHub 读取范围。", 403)
        now = time.monotonic()
        cache_key = (url, accept or "application/vnd.github+json")
        immutable = bool(re.search(r"/(?:git/trees|commits)/[0-9a-f]{40}(?:\?|$)", url)
                         or re.search(r"[?&]ref=[0-9a-f]{40}(?:&|$)", url))
        repository = re.match(r"/repos/([^/]+/[^/]+)/", parts.path)
        # Recheck public visibility in this client before reusing persistent bytes.
        persist = (immutable and repository is not None
                   and repository[1].casefold() in self._public_repositories)
        disk_key = "\n".join(cache_key)
        cached = self._cache.get(cache_key)
        if cached and cached[0] > now:
            self._cache.move_to_end(cache_key)
            return httpx.Response(200, content=cached[1])
        if persist and (body := await run_io(self._public_cache.get, disk_key)) is not None:
            self._remember(cache_key, body, immutable=True)
            return httpx.Response(200, content=body)
        bucket = "search" if parts.path.startswith("/search/") else "core"
        remaining = max(self._blocked_until.get(bucket, 0), self._blocked_until.get("all", 0)) - now
        if remaining > 0:
            raise SourceError(
                "RATE_LIMITED",
                stage,
                f"GitHub 暂时限制了请求，约 {max(1, int((remaining + 59) // 60))} 分钟后可以重试。",
                429,
                needed_action="稍后重试；已打开的来源仍可阅读。",
            )
        headers = {
            "Accept": accept or "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "concept-to-code-learning",
            "Accept-Encoding": "identity",
        }
        if self._token and parts.hostname == "api.github.com":
            headers["Authorization"] = "Bearer " + self._token
        client = await self._ensure_client()
        for attempt in range(self._retries + 1):
            try:
                async with asyncio.timeout(self._timeout):
                    async with client.stream(method, url, headers=headers) as response:
                        self._network_observation = (time.monotonic(), response.status_code == 200,
                                                     None if response.status_code == 200 else "GITHUB_READ_FAILED")
                        self._interpret(response, url=url, stage=stage, allow_404=allow_404)
                        cap = (
                            8 if stage == "tree" else 2 if stage == "contents" else 1
                        ) * MAX_BODY_BYTES
                        chunks, size = [], 0
                        async for chunk in response.aiter_bytes(chunk_size=16384):
                            size += len(chunk)
                            if size > cap:
                                raise SourceError(
                                    "INVALID_PROVIDER_RESPONSE",
                                    stage,
                                    "响应超过安全读取上限。",
                                    413,
                                )
                            chunks.append(chunk)
                        body = b"".join(chunks)
                self._remember(cache_key, body, immutable=immutable)
                if persist:
                    await run_io(self._public_cache.put, disk_key, body)
                return httpx.Response(200, content=body)
            except (httpx.TransportError, TimeoutError):
                self._network_observation = (time.monotonic(), False, "GITHUB_UNREACHABLE")
                if attempt == self._retries:
                    raise SourceError(
                        "PROVIDER_TIMEOUT",
                        stage,
                        "GitHub 连接失败或响应超时。",
                        504,
                        needed_action="检查网络后重试。",
                    ) from None

    def _remember(self, key, body, *, immutable):
        previous = self._cache.pop(key, None)
        if previous:
            self._cache_size -= len(previous[1])
        self._cache[key] = (time.monotonic() + (86400 if immutable else 120), body)
        self._cache_size += len(body)
        while self._cache_size > 20 * MAX_BODY_BYTES or len(self._cache) > 100:
            self._cache_size -= len(self._cache.popitem(last=False)[1][1])

    def _interpret(self, response, *, url, stage, allow_404):
        status = response.status_code
        if status in (403, 429) and (
            status == 429
            or response.headers.get("x-ratelimit-remaining") == "0"
            or "retry-after" in response.headers
        ):
            try:
                delay = float(response.headers.get("retry-after", "60"))
                if "x-ratelimit-reset" in response.headers:
                    delay = max(delay, float(response.headers["x-ratelimit-reset"]) - time.time())
            except ValueError:
                delay = 60
            # Primary search/core quotas are independent. A secondary limit with
            # Retry-After applies globally, including when quota remains.
            bucket = "all"
            if response.headers.get("x-ratelimit-remaining") == "0":
                bucket = "search" if urlsplit(url).path.startswith("/search/") else "core"
            delay = min(3600, max(1, delay))
            self._blocked_until[bucket] = time.monotonic() + delay
            raise SourceError(
                "RATE_LIMITED",
                stage,
                f"GitHub 暂时限制了请求，约 {max(1, int((delay + 59) // 60))} 分钟后可以重试。",
                429,
                needed_action="等待限流窗口后重试。",
            )
        if status in (401, 403):
            raise SourceError(
                "AUTH_REQUIRED",
                stage,
                "GitHub 拒绝了读取请求。",
                401,
                needed_action="检查专用只读配置；不需要使用仓库管理员密钥。",
            )
        if status == 404:
            raise SourceError("FILE_NOT_FOUND", stage, "指定文件、仓库或版本不存在。", 404)
        if status != 200:
            raise SourceError("REPO_UNAVAILABLE", stage, f"GitHub 返回 HTTP {status}。", 502)
        return response

    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None
        self._cache.clear()
        self._cache_size = 0
        self._public_repositories.clear()
