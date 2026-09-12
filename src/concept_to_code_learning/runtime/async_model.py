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
        self._client = None

    async def _fetch(self, path, body=None, *, on_text=None):
        url = self._prepare(path)
        if isinstance(url, AdapterResult):
            return b"", url
        headers = {"Accept": "application/json"}
        if self._config.api_key:
            headers["Authorization"] = f"Bearer {self._config.api_key}"
        started = time.monotonic()
        try:
            async with asyncio.timeout(self._config.timeout_seconds):
                if self._client is None or self._client.is_closed:
                    self._client = httpx.AsyncClient(
                        trust_env=False,
                        follow_redirects=False,
                        transport=self._transport,
                        timeout=self._config.timeout_seconds,
                        limits=httpx.Limits(max_connections=4, max_keepalive_connections=2),
                    )
                async with self._client.stream(
                    "POST" if body else "GET", url, headers=headers, json=body
                ) as response:
                    if response.status_code != 200:
                        code = {
                            401: "MODEL_AUTH_REQUIRED",
                            403: "MODEL_AUTH_REQUIRED",
                            429: "MODEL_RATE_LIMITED",
                        }.get(response.status_code, "MODEL_HTTP_ERROR")
                        return b"", _failure(code, f"Provider HTTP {response.status_code}.")
                    if on_text and "text/event-stream" in response.headers.get("content-type", ""):
                        return await self._read_stream(response, on_text), self._result(started, 1)
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
        except (ValueError, KeyError, TypeError):
            return b"", _failure("MODEL_MALFORMED_RESPONSE", "The model stream was incomplete or invalid.")

    async def _read_stream(self, response, on_text):
        text, identity, finish, usage, size = "", None, None, None, 0
        async for line in response.aiter_lines():
            size += len(line.encode("utf-8"))
            if size > 1024 * 1024:
                raise ValueError("Stream exceeded byte limit")
            if not line.startswith("data:"):
                continue
            data = line[5:].strip()
            if data == "[DONE]":
                break
            value = json.loads(data)
            if value.get("model") is not None:
                identity = value["model"]
                if identity != self._config.model:
                    raise ValueError("Stream model identity mismatch")
            if value.get("usage"):
                usage = value["usage"]
            choices = value.get("choices", [])
            if choices:
                choice = choices[0]
                if choice.get("index", 0) != 0 or len(choices) != 1:
                    raise ValueError("Unexpected stream choice")
                delta = choice.get("delta", {})
                if delta.get("refusal") or delta.get("tool_calls"):
                    raise ValueError("Unexpected model action")
                chunk = delta.get("content") or ""
                if not isinstance(chunk, str):
                    raise ValueError("Invalid delta")
                text += chunk
                if chunk:
                    on_text(text)
                finish = choice.get("finish_reason") or finish
        if finish is None:
            raise ValueError("Model stream ended before completion")
        value = {"model": identity or self._config.model, "choices": [{
            "message": {"content": text}, "finish_reason": finish}]}
        if usage is not None:
            value["usage"] = usage
        return json.dumps(value).encode("utf-8")

    async def models(self):
        payload, result = await self._fetch("/v1/models")
        if not result.ok:
            return result
        return _checked(result, lambda: _parse_model_ids(payload))

    async def health(self):
        result = await self.models()
        if result.ok and self._config.model not in result.usage["served_models"]:
            return _failure("MODEL_NOT_FOUND", "The configured model is not served here.")
        return result

    async def generate(self, messages, *, max_tokens=None, on_text=None, enable_thinking=None):
        prepared = self._prepare("/v1/chat/completions")
        if isinstance(prepared, AdapterResult):
            return prepared
        try:
            prompt_chars, _ = self._validate_messages(messages)
        except ValueError as exc:
            return _failure(str(exc).split(":", 1)[0], str(exc))
        extensions = {}
        if self._config.structured_output:
            extensions["response_format"] = {
                "type": "json_schema",
                "json_schema": {"name": "c2c_object", "schema": {"type": "object"}},
            }
            if enable_thinking is not None:
                extensions["chat_template_kwargs"] = {"enable_thinking": enable_thinking}
        payload, result = await self._fetch(
            "/v1/chat/completions",
            {
                "model": self._config.model,
                "messages": messages,
                "temperature": 0,
                "max_tokens": min(
                    max_tokens or self._config.max_output_tokens, self._config.max_output_tokens
                ),
                "stream": bool(on_text),
                # Some Qwen MLX conversions retain the base model's end-of-text
                # token. Stop at ChatML's turn boundary instead of leaking it into JSON.
                **({"stop": ["<|im_end|>"]} if "qwen" in self._config.model.casefold() else {}),
                **({"stream_options": {"include_usage": True}} if on_text else {}),
                **extensions,
            },
            on_text=on_text,
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
        if self._client is not None:
            await self._client.aclose()
