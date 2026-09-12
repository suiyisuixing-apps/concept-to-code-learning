import importlib.util
import json
import socket
from pathlib import Path

import pytest


@pytest.mark.parametrize("structured", [False, True])
def test_desktop_propagates_application_failure_after_ready(
    structured, tmp_path, monkeypatch, capsys
):
    path = Path(__file__).resolve().parents[1] / "scripts" / "desktop.py"
    spec = importlib.util.spec_from_file_location("desktop_launcher", path)
    desktop = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(desktop)

    checkout = tmp_path / "workspace 中文"
    (checkout / "scripts").mkdir(parents=True)
    (checkout / "apps" / "web" / "dist").mkdir(parents=True)
    (checkout / "apps" / "web" / "dist" / "index.html").write_text("", encoding="utf-8")
    # A real child process exposes the readiness endpoint, then fails. It is a
    # synthetic workbench, not an application or model integration acceptance.
    (checkout / "scripts" / "start.py").write_text(
        """import argparse
import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

(Path(os.environ["C2C_DATA_DIR"]) / "fixture-env.json").write_text(
    json.dumps({"structured": os.environ.get("C2C_MODEL_STRUCTURED_OUTPUT")}),
    encoding="utf-8",
)

parser = argparse.ArgumentParser()
parser.add_argument("--port", type=int)
args = parser.parse_args()

class ReadyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b"{}")

with HTTPServer(("127.0.0.1", args.port), ReadyHandler) as server:
    server.timeout = 5
    server.handle_request()
raise SystemExit(37)
""",
        encoding="utf-8",
    )
    app_dir = tmp_path / "app data"
    config = tmp_path / "desktop.json"
    config.write_text(json.dumps({"model_base_url": "http://127.0.0.1:12345/v1",
                                 "model_id": "fixture", "model_structured_output": structured}),
                      encoding="utf-8")
    # An inherited flag must not override the explicit desktop configuration.
    monkeypatch.setenv("C2C_MODEL_STRUCTURED_OUTPUT", "1")
    monkeypatch.setattr(desktop, "ROOT", checkout)
    monkeypatch.setattr(desktop, "app_directory", lambda: app_dir)
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]

    result = desktop.main(["--config", str(config), "--port", str(port), "--no-browser"])

    assert "学习工作台已启动" in capsys.readouterr().out
    assert result == 37
    captured = json.loads((app_dir / "data" / "fixture-env.json").read_text(encoding="utf-8"))
    assert captured["structured"] == ("1" if structured else None)
