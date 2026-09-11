"""Generated contract drift, portable Skill commands and local HTTP smoke."""

import http.client
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
from concept_to_code_learning.full_learning.providers import ProviderSettings, build_providers


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


def test_member_factories_receive_only_their_role_configuration(monkeypatch, tmp_path):
    from types import SimpleNamespace
    captured = {}
    def module(name):
        def factory(settings):
            captured[name] = settings
            return object()
        return SimpleNamespace(build_provider=factory)
    monkeypatch.setattr("concept_to_code_learning.full_learning.providers.importlib.import_module", module)
    settings = ProviderSettings(ROOT, tmp_path, github_token="source-only",
        model_base_url="http://127.0.0.1:9000", model_id="test-model", model_api_key="model-only",
        authorized_local_roots=(tmp_path,))
    build_providers(settings)
    document = captured["concept_to_code_learning.documents.full"]
    sources = captured["concept_to_code_learning.github_intelligence.full"]
    tutor = captured["concept_to_code_learning.tutor.full"]
    assert document.github_token is None and document.model_api_key is None
    assert document.authorized_local_roots == () and document.model_base_url is None
    assert sources.github_token == "source-only" and sources.authorized_local_roots == (tmp_path,)
    assert sources.model_api_key is None and sources.model_base_url is None
    assert tutor.model_api_key == "model-only" and tutor.model_id == "test-model"
    assert tutor.github_token is None and tutor.authorized_local_roots == ()


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
        # Windows needs its system directory to initialize Winsock in a child.
        # Retain only OS runtime paths, never provider credentials or proxy settings.
        env.update({k: os.environ[k] for k in ("SYSTEMROOT", "WINDIR") if k in os.environ})
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
        # Paired transport control: same service, context, question, source scope and
        # provider doubles; this does not measure a real model or host Skill benefit.
        direct = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
        try:
            direct.request("GET", f'/api/learning/v1/sessions/{explanation["session_id"]}')
            response = direct.getresponse()
            frozen = json.loads(response.read())
            assert response.status == 200
            direct.request("POST", "/api/learning/v1/explanations", body=json.dumps({
                "session_id": frozen["session_id"], "context_revision": frozen["context_revision"],
                "question": "解释梯度下降", "level": explanation["explanation"]["level"],
                "scope": {"source_mode": "specified_public", "repository_allowlist": ["fixture/repo-a"],
                          "network_authorized": True}}, ensure_ascii=False).encode("utf-8"),
                headers={"Content-Type": "application/json"})
            response = direct.getresponse()
            without_skill = json.loads(response.read())
            assert response.status == 200
        finally:
            direct.close()
        for key in ("mode", "status"):
            assert without_skill[key] == explanation[key]
        for key in ("question", "context_snapshot", "level", "answer_sections", "provider_info"):
            assert without_skill["explanation"][key] == explanation["explanation"][key]
        for key in ("repository_url", "commit_sha", "file_path", "excerpt_sha256", "execution_status"):
            assert without_skill["sources"][0][key] == explanation["sources"][0][key]
        assert app.state.learning_service.store.list_notes()[1] == 0
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
