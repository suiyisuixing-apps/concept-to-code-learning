"""Localhost-only fake-service tests for the OpenAI-compatible adapter (Issue #12).

Every endpoint used here is 127.0.0.1 or an unbindable port used as a failure
simulation; no test contacts a real network, model, or cloud service.
"""

import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from concept_to_code_learning.runtime.local_model import (
    ERROR_EMPTY,
    ERROR_HTTP,
    ERROR_MALFORMED,
    ERROR_NOT_CONFIGURED,
    ERROR_TIMEOUT,
    ERROR_UNAUTHORIZED_HOST,
    MODEL_OFFLINE,
    LocalModelAdapter,
    LocalModelConfig,
    is_loopback_host,
)

API_KEY = "sk-TEST-SECRET-DO-NOT-LEAK"
MESSAGES = [{"role": "user", "content": "解释依赖注入"}]


class _FakeServer(ThreadingHTTPServer):
    """Cassettes: each GET /v1/models or POST /v1/chat/completions pops one reply.

    A reply payload of ``float`` means "sleep that many seconds then stay silent"
    (server-side hang simulation). ``None`` payload means "close without answering".
    """

    daemon_threads = True  # a hung slow-reply thread must never block server_close()

    def __init__(self, replies):
        self.replies = list(replies)
        self.seen_headers = []
        self.seen_bodies = []
        super().__init__(("127.0.0.1", 0), _Handler)


class _Handler(BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802
        self._respond()

    def do_POST(self):  # noqa: N802
        length = int(self.headers.get("Content-Length", 0))
        try:
            self.server.seen_bodies.append(json.loads(self.rfile.read(length)))
        except (json.JSONDecodeError, ValueError):
            self.server.seen_bodies.append({})
        self._respond()

    def _respond(self):
        self.server.seen_headers.append(dict(self.headers))
        status, payload = self.server.replies.pop(0) if self.server.replies else (500, "exhausted")
        if isinstance(payload, float):
            time.sleep(payload)
            return
        if payload is None:
            self.close_connection = True
            return
        body = payload if isinstance(payload, bytes) else json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass  # keep pytest output clean


def completion(text, usage=None):
    body = {"choices": [{"message": {"role": "assistant", "content": text}}]}
    if usage is not None:
        body["usage"] = usage
    return body


@pytest.fixture
def serve():
    servers = []

    def start(replies):
        server = _FakeServer(replies)
        servers.append(server)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        return server

    yield start
    for server in servers:
        server.shutdown()
        server.server_close()


def endpoint(server) -> str:
    return f"http://127.0.0.1:{server.server_address[1]}/v1"


def make(base_url, **overrides) -> LocalModelAdapter:
    settings = {"model": "my-local-model", "api_key": API_KEY,
                "timeout_seconds": 5, "max_retries": 0, **overrides}
    return LocalModelAdapter(LocalModelConfig(base_url, **settings))


# -- configuration honesty -----------------------------------------------------


def test_unconfigured_adapter_reports_failure_and_contacts_nothing():
    adapter = LocalModelAdapter(None)
    assert adapter.configured is False
    for result in (adapter.health(), adapter.generate(MESSAGES)):
        assert not result.ok
        assert result.error_code == ERROR_NOT_CONFIGURED
        assert result.attempts == 0
        assert result.text is None


def test_remote_host_requires_explicit_authorization():
    config = LocalModelConfig(base_url="https://api.openai.example/v1", model="m")
    with pytest.raises(ValueError, match=ERROR_UNAUTHORIZED_HOST):
        config.endpoint("/v1/models")
    # Loopback plaintext is allowed; a remote endpoint must be https and authorized.
    assert LocalModelConfig("http://127.0.0.1:9/v1", "m").endpoint("/v1/models")
    with pytest.raises(ValueError, match=ERROR_UNAUTHORIZED_HOST):
        LocalModelConfig("http://203.0.113.7:8000/v1", "m",
                         allow_remote_endpoint=True).endpoint("/v1/models")
    assert LocalModelConfig("https://203.0.113.7:8000/v1", "m",
                            allow_remote_endpoint=True).endpoint("/v1/models")


@pytest.mark.parametrize("bad", ["not-a-url", "ftp://127.0.0.1/x", "http://127.0.0.1:9?k=1"])
def test_invalid_base_url_fails_before_any_request(bad):
    result = LocalModelAdapter(LocalModelConfig(bad, "m")).health()
    assert not result.ok
    assert result.attempts == 0
    assert "INVALID_CONFIG" in (result.detail or "")


def test_loopback_detection_only_accepts_loopback_literals():
    assert is_loopback_host("localhost") and is_loopback_host("127.0.0.1")
    assert not is_loopback_host("example.com") and not is_loopback_host("8.8.8.8")


# -- happy paths ---------------------------------------------------------------


def test_generate_converts_provider_answer_with_usage_and_latency(serve):
    server = serve([(200, completion("  依赖注入就是把依赖交给外部。  ",
                                     {"prompt_tokens": 7, "completion_tokens": 9}))])
    result = make(endpoint(server)).generate(MESSAGES)
    assert result.ok and result.attempts == 1
    assert result.text == "依赖注入就是把依赖交给外部。"
    assert result.model_id == "my-local-model"
    assert result.latency_ms is not None and result.latency_ms >= 0
    assert result.usage["provider_usage"] == {"prompt_tokens": 7, "completion_tokens": 9}
    assert result.usage["token_usage_estimated"] is False
    assert result.usage["prompt_chars"] == len(MESSAGES[0]["content"])
    assert result.usage["estimated_completion_tokens"] >= 1


def test_request_shape_authorization_and_health(serve):
    server = serve([(200, {"data": [{"id": "my-local-model"}, {"id": "other"}]})])
    result = make(endpoint(server)).health()
    assert result.ok and result.model_id == "my-local-model"
    assert result.usage["served_models"] == ["my-local-model", "other"]
    headers = server.seen_headers[0]
    assert headers["Authorization"] == f"Bearer {API_KEY}"
    assert headers["Accept"] == "application/json"


def test_estimated_usage_labelled_when_provider_omits_it(serve):
    server = serve([(200, completion("ok"))])
    result = make(endpoint(server)).generate(MESSAGES)
    assert result.ok
    assert result.usage["provider_usage"] is None
    assert result.usage["token_usage_estimated"] is True


def test_completion_request_caps_output_and_disables_stream(serve):
    server = serve([(200, completion("ok"))])
    make(endpoint(server), max_output_tokens=42).generate(MESSAGES)
    body = server.seen_bodies[0]
    assert body["model"] == "my-local-model"
    assert body["max_tokens"] == 42
    assert body["stream"] is False
    assert body["messages"] == MESSAGES


# -- failure paths: never fake success ------------------------------------------


def test_connection_refused_is_model_offline_not_a_fake_answer(serve):
    server = serve([])
    port = server.server_address[1]
    server.shutdown()
    server.server_close()
    result = make(f"http://127.0.0.1:{port}/v1").generate(MESSAGES)
    assert not result.ok
    assert result.error_code == MODEL_OFFLINE
    assert result.text is None
    assert result.attempts == 1


def test_timeout_is_reported_and_never_retried_as_success(serve):
    server = serve([(200, 30.0)])  # server hangs far past the client timeout
    result = make(endpoint(server), timeout_seconds=0.3).generate(MESSAGES)
    assert not result.ok
    assert result.error_code == ERROR_TIMEOUT
    assert result.attempts == 1


def test_retries_are_bounded_on_offline_endpoint(serve):
    # Bind once, then close: the free ephemeral port reliably refuses on loopback.
    server = serve([])
    offline_url = f"http://127.0.0.1:{server.server_address[1]}/v1"
    server.shutdown()
    server.server_close()
    result = make(offline_url, max_retries=2).health()
    assert not result.ok
    assert result.error_code == MODEL_OFFLINE
    assert result.attempts == 3


@pytest.mark.parametrize("status", [400, 401, 404, 429, 500, 503])
def test_http_errors_are_reported_honestly_without_retry(serve, status):
    server = serve([(status, {"error": {"message": "provider said no"}}),
                    (200, "second reply must never be consumed")])
    result = make(endpoint(server), max_retries=2).generate(MESSAGES)
    assert not result.ok
    assert result.error_code == ERROR_HTTP
    assert result.attempts == 1  # HTTP-level answers are final, not transport retries
    assert str(status) in (result.detail or "")
    assert len(server.replies) == 1


def test_malformed_payloads_are_rejected(serve):
    cases = [
        b"not json at all",
        json.dumps({"choices": []}).encode(),
        json.dumps({"choices": [{"message": {}}]}).encode(),
        json.dumps({"nope": 1}).encode(),
    ]
    for payload in cases:
        server = serve([(200, payload)])
        result = make(endpoint(server)).generate(MESSAGES)
        assert not result.ok and result.error_code == ERROR_MALFORMED, payload


def test_health_malformed_models_payload_is_malformed(serve):
    server = serve([(200, {"data": "not-a-list"})])
    result = make(endpoint(server)).health()
    assert not result.ok and result.error_code == ERROR_MALFORMED


def test_empty_or_refused_completion_is_visible(serve):
    for payload, expected in [
        (completion("   "), ERROR_EMPTY),
        ({"choices": [{"message": {"role": "assistant", "content": "", "refusal": "no"}}]},
         ERROR_EMPTY),
    ]:
        server = serve([(200, payload)])
        result = make(endpoint(server)).generate(MESSAGES)
        assert not result.ok and result.error_code == expected


def test_redirects_are_never_followed():
    redirected_requests = []
    original_bodies = []

    class DestinationHandler(BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802
            redirected_requests.append(self.path)
            self.send_response(200)
            self.send_header("Content-Length", "0")
            self.end_headers()

        do_POST = do_GET

        def log_message(self, *args):
            pass

    destination = ThreadingHTTPServer(("127.0.0.1", 0), DestinationHandler)

    class RedirectHandler(BaseHTTPRequestHandler):
        def do_POST(self):  # noqa: N802
            # Consume the POST before closing the socket. An unread request body
            # can reset the connection on Windows instead of delivering the 302.
            original_bodies.append(self.rfile.read(int(self.headers["Content-Length"])))
            self.send_response(302)
            self.send_header("Location", f"http://127.0.0.1:{destination.server_port}/stolen")
            self.send_header("Content-Length", "0")
            self.end_headers()

        def log_message(self, *args):
            pass

    forward = ThreadingHTTPServer(("127.0.0.1", 0), RedirectHandler)
    servers = (destination, forward)
    threads = [threading.Thread(target=server.serve_forever, daemon=True) for server in servers]
    for thread in threads:
        thread.start()
    try:
        result = make(f"http://127.0.0.1:{forward.server_address[1]}/v1").generate(MESSAGES)
        assert not result.ok
        assert result.error_code == ERROR_HTTP  # 3xx surfaces as an error, no follow
        assert "302" in (result.detail or "")
        assert len(original_bodies) == 1
        assert json.loads(original_bodies[0])["messages"] == MESSAGES
        assert redirected_requests == []
    finally:
        for server, thread in zip(servers, threads, strict=True):
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)


# -- input/output limits and key hygiene ----------------------------------------


def test_input_over_limit_fails_before_any_traffic(serve):
    server = serve([])
    adapter = make(endpoint(server), max_input_chars=10)
    result = adapter.generate([{"role": "user", "content": "字" * 50}])
    assert not result.ok
    assert result.error_code == "INPUT_TOO_LARGE"
    assert result.attempts == 0
    assert server.seen_headers == []  # rejected client-side, zero traffic


def test_invalid_message_shape_fails_before_any_traffic(serve):
    adapter = make(endpoint(serve([])))
    for bad in ([], [{"role": "user"}], [{"role": "user", "content": 42, "extra": "x"}]):
        result = adapter.generate(bad)
        assert not result.ok
        assert result.error_code == "INVALID_REQUEST"
        assert result.attempts == 0


def test_api_key_never_leaks_into_result_details(serve):
    server = serve([(401, {"error": "bad key"})])
    result = make(endpoint(server)).generate(MESSAGES)
    assert not result.ok
    flat = json.dumps(result.__dict__, default=str, ensure_ascii=False)
    assert API_KEY not in flat


def test_proxy_env_is_never_used(serve, monkeypatch):
    # A malicious/accidental proxy setting must not silently route us to the internet.
    monkeypatch.setenv("HTTP_PROXY", "http://127.0.0.1:9")
    monkeypatch.setenv("http_proxy", "http://127.0.0.1:9")
    server = serve([(200, completion("still direct"))])
    result = make(endpoint(server)).generate(MESSAGES)
    assert result.ok and result.text == "still direct"
    assert server.seen_bodies  # the fake server answered directly
