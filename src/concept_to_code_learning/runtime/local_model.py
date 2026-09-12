"""Explicitly configured local OpenAI-compatible model adapter.

Design constraints (Issue #12):
- Opt-in only: absent configuration yields MODEL_NOT_CONFIGURED; nothing is contacted by default.
- Loopback by default. A non-loopback base_url requires an explicit authorization flag.
- No automatic cloud fallback, no model downloads, no paid services.
- Connection failure / timeout / HTTP error / malformed response are reported honestly as
  failures; a fabricated success response is never returned when the model is unreachable.
- API keys are never logged nor embedded in exception messages or result details.

The adapter speaks the OpenAI-compatible ``/v1/chat/completions`` and ``/v1/models``
endpoints with stdlib only. It records the provider model id, latency, token usage
(estimated values are labelled as estimates) and an error classification per call.
"""

import errno
import json
import math
import socket
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from ipaddress import ip_address
from typing import Any
from urllib.parse import urlsplit

__all__ = [
    "MODEL_OFFLINE",
    "AdapterResult",
    "LocalModelAdapter",
    "LocalModelConfig",
    "is_loopback_host",
]

# Stable error codes. ``MODEL_OFFLINE`` is the honest "not reachable" answer:
# the adapter never disguises an offline model as online and never falls back.
MODEL_OFFLINE = "MODEL_OFFLINE"
ERROR_NOT_CONFIGURED = "MODEL_NOT_CONFIGURED"
ERROR_UNAUTHORIZED_HOST = "MODEL_HOST_NOT_AUTHORIZED"
ERROR_HTTP = "MODEL_HTTP_ERROR"
ERROR_TIMEOUT = "MODEL_TIMEOUT"
ERROR_TRANSPORT = "MODEL_TRANSPORT_ERROR"
ERROR_MALFORMED = "MODEL_MALFORMED_RESPONSE"
ERROR_EMPTY = "MODEL_EMPTY_COMPLETION"
_REFUSED_ERRNOS = {errno.ECONNREFUSED, errno.EHOSTUNREACH, errno.ENETUNREACH,
                   # WinError 10061 / 10065 equivalents on Windows.
                   10061, 10065}

_USER_AGENT = "concept-to-code-learning/0.2 local-adapter"


def _estimate_tokens(text: str) -> int:
    """Deterministic character-based estimate; explicitly labelled as an estimate."""
    return max(1, (len(text) + 3) // 4)


def is_loopback_host(host: str) -> bool:
    """True for ``localhost`` and loopback IP literals (127.0.0.0/8, ::1)."""
    try:
        return ip_address(host).is_loopback
    except ValueError:
        return host == "localhost"


@dataclass(frozen=True)
class LocalModelConfig:
    """One local OpenAI-compatible endpoint, created explicitly by the caller.

    ``allow_remote_endpoint`` gates non-loopback hosts; without it a remote
    base_url is refused with ``MODEL_HOST_NOT_AUTHORIZED`` (data-flow rule).
    """

    base_url: str = field(repr=False)
    model: str
    api_key: str | None = field(default=None, repr=False)
    timeout_seconds: float = 30.0
    max_input_chars: int = 24000
    max_output_tokens: int = 1024
    max_retries: int = 1
    allow_remote_endpoint: bool = False
    # Optional wire extensions for the async workbench adapter only.
    structured_output: bool = False

    def __post_init__(self) -> None:
        for name, value in (("timeout_seconds", self.timeout_seconds),
                            ("max_input_chars", self.max_input_chars),
                            ("max_output_tokens", self.max_output_tokens)):
            if not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
                raise ValueError(f"INVALID_CONFIG: {name} must be positive")
        if type(self.max_retries) is not int or not 0 <= self.max_retries <= 2:
            raise ValueError("INVALID_CONFIG: max_retries must be 0..2")
        if (self.timeout_seconds > 120 or type(self.max_input_chars) is not int
                or self.max_input_chars > 100000 or type(self.max_output_tokens) is not int
                or self.max_output_tokens > 8192 or not self.model.strip()):
            raise ValueError("INVALID_CONFIG: configuration exceeds supported limits")

    def endpoint(self, path: str) -> str:
        parts = urlsplit(self.base_url)
        if parts.scheme not in {"http", "https"} or not parts.netloc:
            raise ValueError("INVALID_CONFIG: base_url must be an absolute http(s) URL")
        if parts.query or parts.fragment:
            raise ValueError("INVALID_CONFIG: base_url must not carry a query or fragment")
        if parts.username is not None or parts.password is not None:
            raise ValueError("INVALID_CONFIG: URL credentials are forbidden")
        try:
            parts.port
        except ValueError:
            raise ValueError("INVALID_CONFIG: invalid endpoint port") from None
        host = parts.hostname or ""
        if not is_loopback_host(host):
            if not self.allow_remote_endpoint:
                raise ValueError(
                    f"{ERROR_UNAUTHORIZED_HOST}: {host!r} is not a loopback address; authorize an"
                    " explicit remote/DGX endpoint only with full data-flow awareness"
                )
            if parts.scheme == "http":
                raise ValueError(
                    f"{ERROR_UNAUTHORIZED_HOST}: plaintext http is only allowed for loopback"
                    " endpoints; a remote endpoint must use https"
                )
        base_path = parts.path.rstrip("/")
        if base_path.endswith("/v1") and path.startswith("/v1/"):
            path = path[3:]
        return f"{parts.scheme}://{parts.netloc}{base_path}{path}"


@dataclass
class AdapterResult:
    """Outcome of one adapter call; ``ok`` is True only for a validated provider answer."""

    ok: bool
    text: str | None = None
    error_code: str | None = None
    detail: str | None = None
    attempts: int = 0
    model_id: str | None = None
    latency_ms: int | None = None
    usage: dict[str, Any] = field(default_factory=dict)
    input_truncated: bool = False


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001
        return None


_NO_REDIRECT_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirect)


class LocalModelAdapter:
    """Talks to one authorized endpoint; every failure path stays visible."""

    def __init__(self, config: LocalModelConfig | None = None):
        self._config = config
        # Never let environment proxy settings (e.g. HTTP_PROXY) silently route the
        # request through an external service: this adapter is direct-connection only.
        self._opener = _NO_REDIRECT_OPENER

    @property
    def configured(self) -> bool:
        return self._config is not None

    # -- health ---------------------------------------------------------------

    def health(self) -> AdapterResult:
        """GET /v1/models. An unreachable or misconfigured endpoint reports MODEL_OFFLINE."""
        prepared = self._prepare("/v1/models")
        if isinstance(prepared, AdapterResult):
            return prepared
        started = time.monotonic()
        payload, error, attempts = self._request(prepared, None)
        if error is not None:
            return error
        result = _checked(self._result(started, attempts),
                          lambda: _parse_model_ids(payload))
        if result.ok and self._config.model not in result.usage["served_models"]:
            return _failure("MODEL_NOT_FOUND", "Configured model is not served by this endpoint.")
        return result

    # -- generation -----------------------------------------------------------

    def generate(self, messages: list[dict[str, str]]) -> AdapterResult:
        """POST /v1/chat/completions with bounded input and validated output."""
        prepared = self._prepare("/v1/chat/completions")
        if isinstance(prepared, AdapterResult):
            return prepared
        try:
            prompt_chars, truncated = self._validate_messages(messages)
        except ValueError as exc:
            code = str(exc).split(":", 1)[0]
            return _failure(code, str(exc))
        body = {
            "model": self._config.model,
            "messages": messages,
            "temperature": 0,
            "max_tokens": self._config.max_output_tokens,
            "stream": False,
        }
        started = time.monotonic()
        payload, error, attempts = self._request(prepared, body)
        if error is not None:
            error.input_truncated = truncated
            return error

        def parse() -> tuple[str, dict | None]:
            return _parse_completion(payload)

        result = _checked(self._result(started, attempts), parse)
        if result.ok:
            identity = _load_json(payload).get("model")
            if identity is not None and identity != self._config.model:
                return _failure("MODEL_IDENTITY_MISMATCH", "Response came from a different model.")
            result.text = result.usage.pop("_text")
            provider_usage = result.usage.pop("_provider_usage", None)
            result.usage = {
                "prompt_chars": prompt_chars,
                "provider_usage": provider_usage,
                "estimated_prompt_tokens": _estimate_tokens(
                    "".join(m["content"] for m in messages)),
                "estimated_completion_tokens": _estimate_tokens(result.text),
                "token_usage_estimated": provider_usage is None,
            }
            result.input_truncated = truncated
        return result

    # -- internals ------------------------------------------------------------

    def _prepare(self, path: str) -> str | AdapterResult:
        if self._config is None:
            return _failure(ERROR_NOT_CONFIGURED, "No local model endpoint is configured.")
        try:
            return self._config.endpoint(path)
        except ValueError as exc:
            code = ERROR_UNAUTHORIZED_HOST if str(exc).startswith(ERROR_UNAUTHORIZED_HOST) \
                else ERROR_NOT_CONFIGURED
            return _failure(code, str(exc))

    def _result(self, started: float, attempts: int) -> AdapterResult:
        return AdapterResult(ok=True, attempts=attempts, model_id=self._config.model,
                             latency_ms=_elapsed_ms(started))

    def _validate_messages(self, messages: list[dict[str, str]]) -> tuple[int, bool]:
        if not isinstance(messages, list) or not messages or len(messages) > 30:
            raise ValueError("INVALID_REQUEST: messages must not be empty")
        for message in messages:
            if (not isinstance(message, dict) or set(message) != {"role", "content"}
                    or not isinstance(message.get("content"), str)
                    or message.get("role") not in {"system", "user", "assistant"}):
                raise ValueError("INVALID_REQUEST: each message needs role and string content")
        total = sum(len(m["content"]) for m in messages)
        if total > self._config.max_input_chars:
            raise ValueError(
                f"INPUT_TOO_LARGE: prompt has {total} chars, limit is {self._config.max_input_chars}"
            )
        return total, False

    def _request(self, url: str, body: dict | None) -> tuple[bytes, AdapterResult | None, int]:
        """One logical request with bounded retries on connection-level failures."""
        data = json.dumps(body).encode("utf-8") if body is not None else None
        attempts = self._config.max_retries + 1
        last_error: AdapterResult | None = None
        for attempt in range(1, attempts + 1):
            request = urllib.request.Request(url, data=data, method="POST" if data else "GET")
            request.add_header("User-Agent", _USER_AGENT)
            request.add_header("Accept", "application/json")
            if data is not None:
                request.add_header("Content-Type", "application/json")
            if self._config.api_key:
                request.add_header("Authorization", f"Bearer {self._config.api_key}")
            try:
                with self._opener.open(request, timeout=self._config.timeout_seconds) as response:
                    payload = response.read(1024 * 1024 + 1)
                    if len(payload) > 1024 * 1024:
                        return b"", _failure(ERROR_MALFORMED, "Response exceeded byte limit."), attempt
                    return payload, None, attempt
            except urllib.error.HTTPError as exc:
                # A 3xx (redirects are refused), 4xx or 5xx from the provider:
                # no retry, classify honestly. The key is never echoed back.
                detail = f"provider returned HTTP {exc.code}"
                exc.close()
                return b"", AdapterResult(ok=False, error_code=ERROR_HTTP, detail=detail,
                                          attempts=attempt, model_id=self._config.model), attempt
            except (urllib.error.URLError, TimeoutError, OSError) as exc:
                reason = getattr(exc, "reason", exc)
                if isinstance(exc, TimeoutError) or isinstance(reason, socket.timeout):
                    code, message = ERROR_TIMEOUT, f"timed out after {self._config.timeout_seconds}s"
                elif _is_refused(reason):
                    code, message = MODEL_OFFLINE, "connection refused (is the model running?)"
                else:
                    code, message = ERROR_TRANSPORT, "transport failed"
                last_error = AdapterResult(
                    ok=False, error_code=code,
                    detail=message,
                    attempts=attempt, model_id=self._config.model)
        assert last_error is not None
        return b"", last_error, attempts


def _checked(result: AdapterResult, parse) -> AdapterResult:  # noqa: ANN001
    try:
        payload = parse()
    except _ProviderError as exc:
        result.ok = False
        result.error_code = exc.code
        result.detail = str(exc)
        return result
    if isinstance(payload, tuple):
        text, provider_usage = payload
        result.usage = {"_text": text, "_provider_usage": provider_usage}
    else:
        result.usage = {"served_models": payload}
    return result


class _ProviderError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def _is_refused(reason: Any) -> bool:
    return isinstance(reason, OSError) and getattr(reason, "errno", None) in _REFUSED_ERRNOS


def _elapsed_ms(started: float) -> int:
    return int((time.monotonic() - started) * 1000)


def _parse_model_ids(payload: bytes) -> list[str]:
    data = _load_json(payload)
    try:
        entries = data["data"]
    except (KeyError, TypeError) as exc:
        raise _ProviderError(ERROR_MALFORMED, f"/v1/models response is not valid: {exc}") from exc
    if not isinstance(entries, list):
        raise _ProviderError(ERROR_MALFORMED, "/v1/models response is not valid: data is not a list")
    model_ids = [item["id"] for item in entries
                 if isinstance(item, dict) and isinstance(item.get("id"), str)]
    if not model_ids:
        raise _ProviderError(ERROR_MALFORMED, "/v1/models returned no model ids")
    return model_ids


def _parse_completion(payload: bytes) -> tuple[str, dict | None]:
    data = _load_json(payload)
    try:
        message = data["choices"][0]["message"]
    except (KeyError, IndexError, TypeError) as exc:
        raise _ProviderError(ERROR_MALFORMED, "chat completion response is not valid") from exc
    if not isinstance(message, dict) or not isinstance(message.get("content"), str):
        raise _ProviderError(ERROR_MALFORMED, "message.content is missing or not a string")
    if message.get("refusal"):
        raise _ProviderError(ERROR_EMPTY, "the model refused to answer")
    if data["choices"][0].get("finish_reason") == "length":
        raise _ProviderError("MODEL_OUTPUT_TRUNCATED", "Model reached its output limit.")
    text = message["content"].strip()
    if not text:
        raise _ProviderError(ERROR_EMPTY, "the model returned an empty completion")
    usage = data.get("usage")
    if not (isinstance(usage, dict) and all(type(usage.get(k)) is int and usage[k] >= 0
                                         for k in ("prompt_tokens", "completion_tokens"))):
        usage = None
    elif usage is not None:
        usage = {k: usage[k] for k in ("prompt_tokens", "completion_tokens")}
    return text, usage if isinstance(usage, dict) else None


def _load_json(payload: bytes) -> Any:
    try:
        return json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise _ProviderError(ERROR_MALFORMED, "response is not valid JSON") from exc


def _failure(code: str, detail: str) -> AdapterResult:
    return AdapterResult(ok=False, error_code=code, detail=detail, attempts=0)
