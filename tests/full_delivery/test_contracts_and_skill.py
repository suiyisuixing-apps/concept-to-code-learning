"""Generated contract drift, portable Skill commands and local HTTP smoke."""

import importlib.util
import json
import os
import socket
import subprocess
import sys
import threading
import time
import zipfile

import pytest
import uvicorn
from conftest import ROOT, activate, explain_body
from jsonschema import Draft202012Validator

from concept_to_code_learning.full_contracts import models as m
from concept_to_code_learning.full_contracts.compat import from_sprint_context, to_sprint_context
from concept_to_code_learning.full_learning.errors import LearningError
from concept_to_code_learning.full_learning.providers import ProviderSettings


def test_generated_contracts_and_openapi_match_the_python_models():
    result = subprocess.run([sys.executable, "scripts/export_full_contracts.py", "--check"],
                            cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
    assert result.returncode == 0, result.stdout + result.stderr


def test_runtime_payloads_validate_against_public_schema_and_openapi(client):
    session = activate(client)
    result = client.post("/api/learning/v1/explanations", json=explain_body(session)).json()
    for name, value in (("SessionRecord", session), ("DocumentContext", session["context"]),
                        ("ExplanationResult", result), ("GroundedExplanation", result["explanation"]),
                        ("CodeEvidence", result["sources"][0])):
        schema = json.loads((ROOT / f"schemas/full-delivery-v1/{name}.schema.json").read_text(encoding="utf-8"))
        Draft202012Validator(schema).validate(value)
        with pytest.raises(Exception):
            Draft202012Validator(schema).validate(value | {"verified": True})
    operation = client.get("/openapi.json").json()["paths"]["/api/learning/v1/explanations"]["post"]
    assert operation["requestBody"]["content"]["application/json"]["schema"]["$ref"].endswith("ExplanationRequest")


def test_old_context_roundtrip_without_expanding_the_old_schema(client):
    example = client.get("/api/sprint-1/session").json()["fixture_example"]
    old = client.post("/api/sprint-1/documents/context", json=example["document"]).json()
    full = from_sprint_context(old)
    assert full.mode == "FIXTURE"
    assert to_sprint_context(full) == old
    full.source_type = "PDF"
    with pytest.raises(LearningError, match="INCOMPATIBLE_CONTRACT"):
        to_sprint_context(full)


def test_settings_do_not_reuse_owner_tokens_or_allow_unapproved_remote_models(monkeypatch, tmp_path):
    monkeypatch.setenv("GH_TOKEN", "owner-secret-never-forward")
    monkeypatch.delenv("C2C_GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("C2C_MODEL_BASE_URL", raising=False)
    settings = ProviderSettings.from_env(ROOT, tmp_path)
    assert settings.github_token is None and "owner-secret" not in repr(settings)
    monkeypatch.setenv("C2C_MODEL_BASE_URL", "https://remote.invalid/v1")
    monkeypatch.delenv("C2C_MODEL_NETWORK_AUTHORIZED", raising=False)
    with pytest.raises(LearningError, match="INVALID_CONFIGURATION"):
        ProviderSettings.from_env(ROOT, tmp_path)
    monkeypatch.setenv("C2C_MODEL_NETWORK_AUTHORIZED", "1")
    monkeypatch.setenv("C2C_MODEL_API_KEY", "private-model-key")
    assert "private-model-key" not in repr(ProviderSettings.from_env(ROOT, tmp_path))


def load_client(path):
    spec = importlib.util.spec_from_file_location("portable_learning_client", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("url", ["https://example.org", "http://127.0.0.1.evil.invalid",
                                 "http://user:key@localhost:9000", "http://127.0.0.1/x"])
def test_skill_cannot_send_documents_to_an_arbitrary_endpoint(url):
    module = load_client(ROOT / "scripts/learning_client.py")
    with pytest.raises(module.ClientError, match="ENDPOINT_NOT_AUTHORIZED"):
        module.Client(url)


def test_portable_skill_package_runs_complete_controlled_http_workflow(app, tmp_path):
    package = tmp_path / "skill.zip"
    subprocess.run([sys.executable, "scripts/package_skill.py", "--output", str(package)],
                   cwd=ROOT, check=True, capture_output=True)
    unpack = tmp_path / "unpacked"
    with zipfile.ZipFile(package) as archive:
        assert len(archive.namelist()) == 3
        archive.extractall(unpack)
    skill = unpack / "concept-to-code-learning"
    file = tmp_path / "学习 材料.pdf"
    file.write_bytes(b"CONTROLLED-TRANSPORT-PROBE")
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port,
                                         log_level="error", access_log=False))
    thread = threading.Thread(target=server.run, kwargs={"sockets": [sock]}, daemon=True)
    thread.start()
    try:
        deadline = time.monotonic() + 5
        while not server.started and time.monotonic() < deadline:
            time.sleep(0.01)
        assert server.started
        # No GitHub/model credentials, proxies or user data directory are inherited.
        env = {"PATH": os.defpath, "HOME": str(tmp_path), "PYTHONIOENCODING": "gbk"}
        def run(*args, success=True):
            result = subprocess.run([sys.executable, str(skill / "scripts/learning_client.py"),
                "--base-url", f"http://127.0.0.1:{port}", *args], cwd=tmp_path, env=env,
                capture_output=True, text=True, encoding="utf-8", timeout=15)
            assert (result.returncode == 0) == success, result.stdout + result.stderr
            return result
        caps = json.loads(run("capabilities").stdout)
        assert caps["integrated_product"] == "FIXTURE"
        explanation = json.loads(run("learn", "--file", str(file), "--question", "解释梯度下降", "--repo",
            "fixture/repo-a", "--network-authorized", "--selected-text", "梯度下降 😀").stdout)
        assert explanation["mode"] == "FIXTURE" and explanation["status"] == "COMPLETE"
        session_id, explanation_id = explanation["session_id"], explanation["explanation"]["explanation_id"]
        args = ["save", "--session-id", session_id, "--explanation-id", explanation_id,
                "--idempotency-key", "skill-smoke-save", "--title", "学习笔记 😀"]
        run(*args, success=False)
        assert app.state.learning_service.store.list_notes()[1] == 0
        note = json.loads(run(*args, "--confirm").stdout)
        assert note["title"] == "学习笔记 😀"
        assert json.loads(run(*args, "--confirm").stdout) == note
        exported = run("export-note", "--note-id", note["note_id"], "--format", "markdown").stdout
        assert "学习笔记 😀" in exported and note["snapshot_sha256"] in exported
        assert json.loads(run("notes").stdout)["total"] == 1
        run("delete-note", "--note-id", note["note_id"], "--revision", "1", success=False)
        run("delete-note", "--note-id", note["note_id"], "--revision", "1", "--confirm")
        assert json.loads(run("notes").stdout)["total"] == 0
    finally:
        server.should_exit = True
        thread.join(timeout=5)
        sock.close()
        assert not thread.is_alive()


def test_document_changed_after_selection_is_rejected_before_model(client, providers):
    session = activate(client)
    providers.document.records["doc-PDF"].revision = 2
    response = client.post("/api/learning/v1/explanations", json=explain_body(session))
    assert response.status_code == 409 and response.json()["code"] == "DOCUMENT_VERSION_MISMATCH"
    assert providers.tutor.plan_count == 0


def test_live_usage_cannot_be_invented_when_unobserved():
    with pytest.raises(ValueError):
        m.Metrics(latency_ms=1, input_tokens=999, token_source="UNAVAILABLE")
