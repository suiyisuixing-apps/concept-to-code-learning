"""Cancellable production transport sharing the member adapter's strict parser."""

import asyncio
import json
import time

import httpx

from .local_model import (
    AdapterResult,
    LocalModelAdapter,
    _checked,
    _estimate_tokens,
    _failure,
    _parse_completion,
    _parse_model_ids,
)


class AsyncLocalModelAdapter(LocalModelAdapter):
    def __init__(self, config=None, *, transport=None):
        super().__init__(config)
        self._transport = transport

    async def _fetch(self, path, body=None):
        url = self._prepare(path)
        if isinstance(url, AdapterResult):
            return b"", url
        headers = {"Accept": "application/json"}
        if self._config.api_key:
            headers["Authorization"] = f"Bearer {self._config.api_key}"
        started = time.monotonic()
        try:
            # Closing each logical call makes cancellation release the socket too.
            async with asyncio.timeout(self._config.timeout_seconds):
                async with httpx.AsyncClient(
                    trust_env=False,
                    follow_redirects=False,
                    transport=self._transport,
                    timeout=self._config.timeout_seconds,
                ) as client:
                    async with client.stream(
                        "POST" if body else "GET", url, headers=headers, json=body
                    ) as response:
                        if response.status_code != 200:
                            code = {
                                401: "MODEL_AUTH_REQUIRED",
                                403: "MODEL_AUTH_REQUIRED",
                                429: "MODEL_RATE_LIMITED",
                            }.get(response.status_code, "MODEL_HTTP_ERROR")
                            return b"", _failure(code, f"Provider HTTP {response.status_code}.")
                        chunks, size = [], 0
                        async for chunk in response.aiter_bytes(chunk_size=16384):
                            size += len(chunk)
                            if size > 1024 * 1024:
                                return b"", _failure(
                                    "MODEL_MALFORMED_RESPONSE", "Response exceeded byte limit."
                                )
                            chunks.append(chunk)
                        return b"".join(chunks), self._result(started, 1)
        except (TimeoutError, httpx.TimeoutException):
            return b"", _failure("MODEL_TIMEOUT", "The configured model timed out.")
        except httpx.TransportError:
            return b"", _failure("MODEL_OFFLINE", "The configured model could not be reached.")

    async def health(self):
        payload, result = await self._fetch("/v1/models")
        if not result.ok:
            return result
        result = _checked(result, lambda: _parse_model_ids(payload))
        if result.ok and self._config.model not in result.usage["served_models"]:
            return _failure("MODEL_NOT_FOUND", "The configured model is not served here.")
        return result

    async def generate(self, messages):
        prepared = self._prepare("/v1/chat/completions")
        if isinstance(prepared, AdapterResult):
            return prepared
        try:
            prompt_chars, _ = self._validate_messages(messages)
        except ValueError as exc:
            return _failure(str(exc).split(":", 1)[0], str(exc))
        payload, result = await self._fetch(
            "/v1/chat/completions",
            {
                "model": self._config.model,
                "messages": messages,
                "temperature": 0,
                "max_tokens": self._config.max_output_tokens,
                "stream": False,
            },
        )
        if not result.ok:
            return result
        result = _checked(result, lambda: _parse_completion(payload))
        if not result.ok:
            return result
        identity = json.loads(payload).get("model")
        if identity is not None and identity != self._config.model:
            return _failure("MODEL_IDENTITY_MISMATCH", "Response came from a different model.")
        result.text = result.usage.pop("_text")
        usage = result.usage.pop("_provider_usage")
        result.usage = {
            "provider_usage": usage,
            "prompt_chars": prompt_chars,
            "estimated_prompt_tokens": _estimate_tokens("".join(m["content"] for m in messages)),
            "estimated_completion_tokens": _estimate_tokens(result.text),
            "token_usage_estimated": usage is None,
        }
        return result

    async def close(self):
        return None
