"""Real loopback HTTP transport controls, not model-quality evidence."""

import asyncio
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from concept_to_code_learning.runtime.async_model import AsyncLocalModelAdapter
from concept_to_code_learning.runtime.local_model import LocalModelConfig


@pytest.fixture
def servers():
    opened = []

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802
            self.reply()

        def do_POST(self):  # noqa: N802
            self.rfile.read(int(self.headers.get("content-length", 0)))
            self.reply()

        def reply(self):
            self.server.seen.append(dict(self.headers))
            status, body, headers = self.server.response
            self.send_response(status)
            for name, value in headers.items():
                self.send_header(name, value)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            try:
                self.wfile.write(body)
            except (ConnectionResetError, BrokenPipeError):
                pass

        def log_message(self, *args):
            pass

    def start(status, body, **headers):
        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        server.response = (status, body, headers)
        server.seen = []
        opened.append(server)
        threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.02}, daemon=True).start()
        return server, f"http://127.0.0.1:{server.server_address[1]}/v1"

    yield start
    for server in opened:
        server.shutdown()
        server.server_close()


def test_production_async_transport_bypasses_environment_proxy_and_keeps_key_at_endpoint(servers, monkeypatch):
    endpoint, url = servers(200, b'{"data":[{"id":"test-model"}]}', **{"Content-Type": "application/json"})
    proxy, proxy_url = servers(500, b"proxy must not receive requests")
    for key in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"):
        monkeypatch.setenv(key, proxy_url)
    for key in ("NO_PROXY", "no_proxy"):
        monkeypatch.setenv(key, "")

    async def scenario():
        adapter = AsyncLocalModelAdapter(LocalModelConfig(url, "test-model", api_key="controlled-key"))
        try:
            result = await adapter.health()
            assert result.ok
        finally:
            await adapter.close()
    asyncio.run(scenario())
    assert proxy.seen == []
    assert endpoint.seen[0]["Authorization"] == "Bearer controlled-key"


def test_production_async_redirect_is_not_followed(servers):
    target, target_url = servers(200, b"must not reach this server")
    _, url = servers(302, b"", Location=target_url)

    async def scenario():
        adapter = AsyncLocalModelAdapter(LocalModelConfig(url, "test-model", api_key="controlled-key"))
        try:
            result = await adapter.health()
            assert result.error_code == "MODEL_HTTP_ERROR"
        finally:
            await adapter.close()
    asyncio.run(scenario())
    assert target.seen == []


@pytest.mark.parametrize("stream", [False, True])
def test_production_async_body_limit_including_sse_without_newline(servers, stream):
    payload = b"data: " + b"x" * (1024 * 1024 + 1) if stream else b"x" * (1024 * 1024 + 1)
    _, url = servers(200, payload, **{"Content-Type": "text/event-stream" if stream else "application/json"})

    async def scenario():
        adapter = AsyncLocalModelAdapter(LocalModelConfig(url, "test-model"))
        previews = []
        try:
            result = await adapter.generate([{"role": "user", "content": "hello"}],
                                            on_text=previews.append if stream else None)
            assert result.error_code == "MODEL_MALFORMED_RESPONSE"
            assert previews == []
        finally:
            await adapter.close()
    asyncio.run(scenario())


def test_bounded_sse_keeps_valid_unicode_completion(servers):
    event = {"model": "test-model", "choices": [{"index": 0, "delta": {"content": "中文 😀"}, "finish_reason": "stop"}]}
    _, url = servers(200, ("data: " + json.dumps(event, ensure_ascii=False) + "\n\ndata: [DONE]\n").encode(),
                     **{"Content-Type": "text/event-stream"})

    async def scenario():
        adapter = AsyncLocalModelAdapter(LocalModelConfig(url, "test-model"))
        try:
            result = await adapter.generate([{"role": "user", "content": "hello"}], on_text=lambda text: None)
            assert result.ok and result.text == "中文 😀"
        finally:
            await adapter.close()
    asyncio.run(scenario())


@pytest.mark.parametrize("newline", ["\n", "\r\n", "\r"])
def test_sse_previews_and_finishes_without_waiting_for_eof(newline):
    async def scenario():
        previewed, allow_finish, disconnected = asyncio.Event(), asyncio.Event(), asyncio.Event()

        async def serve(reader, writer):
            try:
                await reader.readuntil(b"\r\n\r\n")
                writer.write(b"HTTP/1.1 200 OK\r\nContent-Type: text/event-stream\r\nTransfer-Encoding: chunked\r\n\r\n")

                async def chunk(text):
                    raw = text.encode("utf-8")
                    # Deliberately split CRLF across transport chunks too.
                    for part in (raw[:-1], raw[-1:]):
                        writer.write(f"{len(part):x}\r\n".encode() + part + b"\r\n")
                        await writer.drain()

                await chunk('data: {"model":"test-model","choices":[{"delta":{"content":"中文 😀"}}]}' + newline * 2)
                await allow_finish.wait()
                await chunk('data: {"choices":[{"delta":{},"finish_reason":"stop"}]}' + newline * 2 + "data: [DONE]" + newline * 2)
                # No terminating chunk: completion must recognize DONE, not EOF.
                while await reader.read(4096):
                    pass
            finally:
                writer.close()
                await writer.wait_closed()
                disconnected.set()

        server = await asyncio.start_server(serve, "127.0.0.1", 0)
        url = f"http://127.0.0.1:{server.sockets[0].getsockname()[1]}/v1"
        adapter = AsyncLocalModelAdapter(LocalModelConfig(url, "test-model", timeout_seconds=5))
        task = asyncio.create_task(adapter.generate([{"role": "user", "content": "hello"}], on_text=lambda text: previewed.set()))
        try:
            await asyncio.wait_for(previewed.wait(), 2)
            assert not task.done()
            allow_finish.set()
            result = await asyncio.wait_for(task, 2)
            assert result.ok and result.text == "中文 😀"
        finally:
            allow_finish.set()
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
            await adapter.close()
            server.close()
            await server.wait_closed()
            await asyncio.wait_for(disconnected.wait(), 2)
    asyncio.run(scenario())
