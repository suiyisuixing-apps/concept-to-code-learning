"""GitHub raw-content and refs client. Token never leaves this module.

Only the allowed GitHub domains are contacted: raw.githubusercontent.com and
api.github.com. Redirects are not followed across hosts. 401/403/404/429 are
surfaced as SourceError; the Authorization header is never logged.
"""

from __future__ import annotations

from typing import Any

import httpx

from .errors import SourceError

# Frozen list of hosts this provider is allowed to contact. No arbitrary URL.
ALLOWED_HOSTS = frozenset({"raw.githubusercontent.com", "api.github.com"})
DEFAULT_TIMEOUT = 10.0
DEFAULT_RETRIES = 1
MAX_BODY_BYTES = 5 * 1024 * 1024  # 5 MiB cap; files above are refused


class GitHubRawClient:
    """Read-only client for raw file content, ref resolution and blob SHA."""

    def __init__(self, *, token: str | None = None, timeout: float = DEFAULT_TIMEOUT,
                 retries: int = DEFAULT_RETRIES):
        # Token is held privately; repr() never exposes it.
        self._token = token
        self._timeout = timeout
        self._retries = max(0, retries)
        self._client: httpx.AsyncClient | None = None

    def _headers(self) -> dict[str, str]:
        headers = {"Accept": "application/vnd.github+json",
                    "X-GitHub-Api-Version": "2022-11-28",
                    "User-Agent": "concept-to-code-learning/source-provider"}
        if self._token:
            # Authorization is only built here and never echoed in exceptions.
            headers["Authorization"] = f"Bearer {self._token}"
        return headers

    async def _ensure_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                headers=self._headers(), timeout=self._timeout,
                follow_redirects=False, trust_env=False)
        return self._client

    async def fetch_raw(self, owner: str, name: str, commit: str, path: str) -> bytes:
        """Fetch raw file bytes pinned to an immutable commit SHA."""
        url = f"https://raw.githubusercontent.com/{owner}/{name}/{commit}/{path}"
        return await self._get_bytes(url, stage="fetch_raw")

    async def resolve_ref(self, owner: str, name: str, ref: str) -> str:
        """Resolve a branch/tag/ref to a 40-char commit SHA."""
        url = f"https://api.github.com/repos/{owner}/{name}/git/refs/{ref}"
        data = await self._get_json(url, stage="resolve_ref")
        try:
            return str(data["object"]["sha"])
        except (KeyError, TypeError) as exc:
            raise SourceError("REF_UNRESOLVED", "resolve_ref",
                               f"GitHub returned an unexpected ref payload for {ref}",
                               status=502, needed_action="Verify the ref exists and the token has read scope.",
                               detail={"ref": ref}) from exc

    async def fetch_blob_sha(self, owner: str, name: str, commit: str, path: str) -> str | None:
        """Fetch the git blob SHA for a path pinned to a commit. Returns None on 404."""
        url = f"https://api.github.com/repos/{owner}/{name}/contents/{path}?ref={commit}"
        try:
            data = await self._get_json(url, stage="fetch_blob_sha")
        except SourceError as exc:
            if exc.code == "FILE_NOT_FOUND":
                return None
            raise
        sha = data.get("sha") if isinstance(data, dict) else None
        return str(sha) if isinstance(sha, str) and len(sha) == 40 else None

    async def fetch_license(self, owner: str, name: str, commit: str, path: str) -> bytes | None:
        """Fetch a candidate license file pinned to the same commit. None if absent."""
        url = f"https://raw.githubusercontent.com/{owner}/{name}/{commit}/{path}"
        try:
            return await self._get_bytes(url, stage="fetch_license", allow_404=True)
        except SourceError as exc:
            if exc.code == "FILE_NOT_FOUND":
                return None
            raise

    async def _get_bytes(self, url: str, *, stage: str, allow_404: bool = False) -> bytes:
        response = await self._request("GET", url, stage=stage, allow_404=allow_404)
        body = response.content
        if len(body) > MAX_BODY_BYTES:
            raise SourceError("INVALID_PROVIDER_RESPONSE", stage,
                              "File exceeds the 5 MiB provider cap",
                              status=413, needed_action="Use a smaller path or pin a narrower excerpt.")
        return body

    async def _get_json(self, url: str, *, stage: str) -> dict[str, Any]:
        response = await self._request("GET", url, stage=stage, allow_404=False,
                                       accept="application/vnd.github+json")
        try:
            return response.json()
        except ValueError as exc:
            raise SourceError("INVALID_PROVIDER_RESPONSE", stage,
                              "GitHub returned a non-JSON payload",
                              status=502, needed_action="Retry; if persistent, report the endpoint.") from exc

    async def _request(self, method: str, url: str, *, stage: str,
                       allow_404: bool = False, accept: str | None = None) -> httpx.Response:
        client = await self._ensure_client()
        last_exc: SourceError | None = None
        for attempt in range(self._retries + 1):
            try:
                response = await client.request(method, url,
                                                headers={"Accept": accept} if accept else None)
            except (httpx.TimeoutException, httpx.TransportError) as exc:
                # Network failure never carries the token; safe to surface.
                last_exc = SourceError("NETWORK_NOT_AUTHORIZED", stage,
                                       "Request to GitHub timed out or failed transport",
                                       status=504, needed_action="Retry once; check proxy and reachability.",
                                       detail={"type": type(exc).__name__})
                continue
            return self._interpret(response, url=url, stage=stage, allow_404=allow_404)
        assert last_exc is not None
        raise last_exc

    def _interpret(self, response: httpx.Response, *, url: str, stage: str,
                   allow_404: bool) -> httpx.Response:
        status = response.status_code
        # Reject any redirect that leaves the allowed hosts.
        if 300 <= status < 400:
            location = response.headers.get("location", "")
            raise SourceError("INVALID_PROVIDER_RESPONSE", stage,
                               "GitHub returned a redirect; cross-host redirects are not followed",
                               status=502, needed_action="Pin to an immutable commit URL.",
                               detail={"location_prefix": location[:120]})
        if status == 404 and allow_404:
            raise SourceError("FILE_NOT_FOUND", stage,
                              "The requested path was not found at the pinned commit",
                              status=404, needed_action="Confirm the path or ref.")
        if status in (401, 403):
            # Never include the Authorization header in the message.
            raise SourceError("AUTH_REQUIRED", stage,
                              "GitHub rejected the request as unauthorized",
                              status=401, needed_action="Provide a token with public_repo read scope.")
        if status == 404:
            raise SourceError("FILE_NOT_FOUND", stage,
                              "The requested path or ref was not found",
                              status=404, needed_action="Confirm the path or ref exists at the commit.")
        if status == 429:
            retry_after = response.headers.get("retry-after")
            reset = response.headers.get("x-ratelimit-reset")
            raise SourceError("RATE_LIMITED", stage,
                              "GitHub rate limit reached",
                              status=429, needed_action="Wait for the reset window then retry.",
                              detail={"retry_after": retry_after, "rate_limit_reset": reset})
        if not (200 <= status < 300):
            raise SourceError("REPO_UNAVAILABLE", stage,
                              f"GitHub returned HTTP {status}",
                              status=502, needed_action="Retry; if persistent, verify the repository visibility.")
        return response

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None
