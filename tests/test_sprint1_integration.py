"""Offline contract, trust-boundary, orchestration and durable-note acceptance tests."""

import json
import socket
import sqlite3
import subprocess
import sys
from contextlib import closing
from copy import deepcopy
from dataclasses import replace
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from concept_to_code_learning.api import create_app
from concept_to_code_learning.contracts import load_schemas, validate_record
from concept_to_code_learning.integration.contracts import NAMES, load_contracts, validate
from concept_to_code_learning.integration.errors import SliceError
from concept_to_code_learning.integration.ports import (
    DocumentSelection,
    SourceRequest,
)
from concept_to_code_learning.integration.providers import (
    ProviderConfig,
    build_providers,
    fixture_request,
)
from concept_to_code_learning.integration.service import VerticalSliceService
from concept_to_code_learning.integration.store import SnapshotNoteStore
from concept_to_code_learning.store import NoteStore
from concept_to_code_learning.tutor.fixture import QUESTION, FixtureTutor

ROOT = Path(__file__).resolve().parents[1]
PREFIX = "/api/sprint-1"
SCHEMAS = load_contracts(ROOT)


def make_service(folder, config=None):
    config = config or ProviderConfig()
    old_store = NoteStore(folder, load_schemas(ROOT))
    notes = SnapshotNoteStore(old_store, SCHEMAS)
    return VerticalSliceService(*build_providers(ROOT, config), notes, SCHEMAS, config)


def explain(service, **overrides):
    body = {**fixture_request(ROOT), **overrides}
    return service.explain(DocumentSelection(**body["document"]), SourceRequest(**body["source"]),
                           body["question"], body["explanation_level"])


@pytest.fixture
def service(tmp_path):
    return make_service(tmp_path)


@pytest.fixture
def client(tmp_path):
    return TestClient(create_app(tmp_path, provider_config=ProviderConfig()))


@pytest.fixture(scope="module")
def records(tmp_path_factory):
    service = make_service(tmp_path_factory.mktemp("sprint-contracts"))
    answer = explain(service)
    note = service.save_note(answer["grounded_explanation_id"], "Snapshot", "My words", True)
    return {"document-context": answer["document_context"],
            "github-code-source": answer["github_sources"][0],
            "grounded-explanation": answer, "saved-note": note}


@pytest.mark.parametrize("name,field", [(name, field) for name in NAMES
                                       for field in SCHEMAS[name]["required"]])
def test_each_required_field_is_enforced(records, name, field):
    invalid = deepcopy(records[name])
    invalid.pop(field)
    with pytest.raises(SliceError, match="Invalid field"):
        validate(name, invalid, SCHEMAS)


def test_nested_contracts_are_identical_and_refs_cannot_use_network(project):
    for name in ("grounded-explanation", "saved-note"):
        for nested in ("document-context", "github-code-source"):
            expected = {k: v for k, v in SCHEMAS[nested].items() if k not in ("title", "$schema")}
            assert SCHEMAS[name]["$defs"][nested] == expected
    path = project / "schemas/sprint-1/document-context.schema.json"
    schema = json.loads(path.read_text(encoding="utf-8"))
    schema["properties"]["file_name"] = {"$ref": "https://example.invalid/schema"}
    path.write_text(json.dumps(schema), encoding="utf-8")
    with pytest.raises(SliceError, match="Cannot load"):
        load_contracts(project)


@pytest.mark.parametrize("level", ["Beginner", "University"])
def test_complete_fixture_api_flow_has_both_sources_and_no_network(client, monkeypatch, level):
    def forbidden(*args, **kwargs):
        raise AssertionError("Default fixture integration must be offline")
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    body = client.get(f"{PREFIX}/session").json()["fixture_example"]
    body["explanation_level"] = level
    context = client.post(f"{PREFIX}/documents/context", json=body["document"])
    assert context.status_code == 200
    source = client.post(f"{PREFIX}/github/verify", json=body["source"])
    assert source.status_code == 200
    response = client.post(f"{PREFIX}/learning/explain", json=body)
    assert response.status_code == 200
    answer = response.json()
    validate("grounded-explanation", answer, SCHEMAS)
    assert answer["document_context"] == context.json()
    assert answer["github_sources"] == [source.json()]
    assert answer["provider_mode"] == "fixture"
    assert answer["mode"] == "FIXTURE" and answer["status"] == "SCAFFOLD_DEMO"
    assert answer["runnable_example_status"] == "NOT_RUN"
    assert answer["document_context"]["source_type"] == "MARKDOWN_FIXTURE"
    assert client.get(f"{PREFIX}/notes").json()["notes"] == []
    saved = client.post(f"{PREFIX}/notes", json={
        "grounded_explanation_id": answer["grounded_explanation_id"], "title": "My note",
        "user_text": "MY OWN WORDS", "save_requested_by_user": True})
    assert saved.status_code == 201
    assert saved.json()["explanation_snapshot"] == answer
    assert client.get(f"{PREFIX}/notes").json()["notes"] == [saved.json()]


@pytest.mark.parametrize("field,value", [("document_id", "other"), ("current_page", 999),
                                        ("current_slide", 1), ("selected_text", "not on this page")])
def test_invalid_document_stops_before_github_or_tutor(service, monkeypatch, field, value):
    def forbidden(*args):
        pytest.fail("Downstream provider ran after a document failure")
    monkeypatch.setattr(service.github, "verify", forbidden)
    monkeypatch.setattr(service.tutor, "explain", forbidden)
    body = fixture_request(ROOT)
    body["document"][field] = value
    with pytest.raises(SliceError):
        explain(service, **body)
    assert service.notes.list() == []


@pytest.mark.parametrize("field,value", [("repository_url", "https://github.com/other/repo"),
                                        ("ref_or_commit", "main"), ("file_path", "missing.py"),
                                        ("symbol", "missing")])
def test_fixture_does_not_substitute_source_for_arbitrary_input(service, field, value):
    body = fixture_request(ROOT)
    body["source"][field] = value
    with pytest.raises(SliceError) as failure:
        explain(service, **body)
    assert failure.value.code == "SOURCE_NOT_FOUND"


@pytest.mark.parametrize("change", ["label_only", "unverified", "wrong_hash", "wrong_lines",
                                   "wrong_commit", "missing_license", "private", "wrong_request"])
def test_forged_verification_cannot_reach_tutor(service, monkeypatch, change):
    request = SourceRequest(**fixture_request(ROOT)["source"])
    receipt = service.github.verify(request)
    source = deepcopy(receipt.source)
    if change == "label_only":
        receipt = replace(receipt, checks=frozenset())
    elif change == "unverified":
        source.update(verification_status="GITHUB_SOURCE_UNVERIFIED",
                      source_status="GITHUB_SOURCE_UNVERIFIED")
    elif change == "wrong_hash":
        source["code_excerpt"] = source["code_excerpt"].replace("commons", "forged")
    elif change == "wrong_lines":
        source["line_end"] += 1
    elif change == "wrong_commit":
        source["commit_sha"] = "0" * 40
    elif change == "missing_license":
        source["license_name"] = None
    elif change == "private":
        source["visibility"] = "private"
    elif change == "wrong_request":
        receipt = replace(receipt, request=replace(request, file_path="other.py"))
    receipt = replace(receipt, source=source)
    monkeypatch.setattr(service.github, "verify", lambda _: receipt)
    def forbidden(*args):
        pytest.fail("Tutor ran on an unverified source")
    monkeypatch.setattr(service.tutor, "explain", forbidden)
    with pytest.raises(SliceError):
        explain(service)
    assert service.notes.list() == []


def test_unverified_status_cannot_claim_verified_in_schema(records):
    source = {**records["github-code-source"], "verification_status": "GITHUB_SOURCE_UNVERIFIED"}
    with pytest.raises(SliceError):
        validate("github-code-source", source, SCHEMAS)


@pytest.mark.parametrize("change", ["execution", "citation", "context", "unsupported", "mode",
                                   "question", "source", "level"])
def test_bad_tutor_output_is_not_remembered(service, monkeypatch, change):
    original = service.tutor.explain
    def altered(context, source, question, level):
        answer = original(context, source, question, level)
        if change == "execution":
            answer["runnable_example_status"] = "VERIFIED_RUNNABLE"
        elif change == "citation":
            answer["document_citations"][0]["quote_hash"] = "0" * 64
        elif change == "context":
            answer["document_context"]["file_hash"] = "0" * 64
        elif change == "unsupported":
            answer["unsupported_claims"] = ["An unsupported assertion"]
        elif change == "mode":
            answer.update(mode="LIVE", status="GROUNDED_ANSWER", provider_mode="openai_compatible")
        elif change == "question":
            answer["question"] = "A different question"
        elif change == "source":
            answer["github_sources"][0]["commit_sha"] = "0" * 40
        elif change == "level":
            answer["explanation_level"] = "University"
        return answer
    monkeypatch.setattr(service.tutor, "explain", altered)
    with pytest.raises(SliceError) as failure:
        explain(service)
    if change == "unsupported":
        assert failure.value.payload()["details"]["unsupported_claims"] == [
            "An unsupported assertion"]
    with closing(service.notes.storage.connect()) as db, db:
        assert db.execute("SELECT count(*) FROM sprint_explanations").fetchone()[0] == 0
    assert service.notes.list() == []


@pytest.mark.parametrize("stage", ["document", "github", "tutor"])
def test_provider_crash_never_returns_success_or_exposes_details(service, monkeypatch, stage):
    def fail(*args):
        raise RuntimeError("/private/school/secret-content.txt token=private")
    method = {"document": "resolve", "github": "verify", "tutor": "explain"}[stage]
    monkeypatch.setattr(getattr(service, stage), method, fail)
    with pytest.raises(SliceError) as failure:
        explain(service)
    assert failure.value.code == "PROVIDER_UNAVAILABLE"
    assert failure.value.stage == stage
    assert "private" not in json.dumps(failure.value.payload())
    assert service.notes.list() == []


@pytest.mark.parametrize("env_key", ["DOCUMENT_PROVIDER", "GITHUB_SOURCE_PROVIDER", "TUTOR_PROVIDER"])
def test_unknown_provider_fails_configuration(env_key):
    with pytest.raises(SliceError) as failure:
        ProviderConfig.from_env({env_key: "typo"})
    assert failure.value.code == "INVALID_PROVIDER"


def test_default_modes_are_fixture():
    assert ProviderConfig.from_env({}).public_modes() == {
        "document": "fixture", "github": "fixture", "tutor": "fixture"}


@pytest.mark.parametrize("config,authorized,code,status", [
    (ProviderConfig(document="pptx"), False, "PROVIDER_NOT_IMPLEMENTED", 501),
    (ProviderConfig(github="github"), False, "NETWORK_NOT_AUTHORIZED", 422),
    (ProviderConfig(github="github"), True, "PROVIDER_NOT_IMPLEMENTED", 501),
    (ProviderConfig(tutor="openai_compatible"), False, "PROVIDER_NOT_CONFIGURED", 503),
    (ProviderConfig(tutor="openai_compatible", tutor_base_url="http://127.0.0.1:8001/v1",
                    tutor_model="explicit-test-model"), False, "PROVIDER_NOT_IMPLEMENTED", 501),
])
def test_real_switches_fail_explicitly_without_network(tmp_path, monkeypatch, config,
                                                       authorized, code, status):
    def forbidden(*args, **kwargs):
        pytest.fail("An unavailable provider attempted a network connection")
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    client = TestClient(create_app(tmp_path, provider_config=config))
    body = fixture_request(ROOT)
    body["source"]["network_authorized"] = authorized
    response = client.post(f"{PREFIX}/learning/explain", json=body)
    assert response.status_code == status
    assert response.json()["code"] == code
    assert response.json()["status"] == "FAILED"
    assert client.get(f"{PREFIX}/notes").json()["notes"] == []
    assert client.get(f"{PREFIX}/session").json()["status"] == "PROVIDERS_UNAVAILABLE"


def test_save_requires_explicit_boolean_and_server_handle(client):
    body = {"grounded_explanation_id": "not-generated", "title": "Title", "user_text": "mine",
            "save_requested_by_user": False}
    response = client.post(f"{PREFIX}/notes", json=body)
    assert response.status_code == 422 and response.json()["code"] == "EXPLICIT_SAVE_REQUIRED"
    assert client.post(f"{PREFIX}/notes", json={**body, "save_requested_by_user": "true"}
                       ).status_code == 422
    response = client.post(f"{PREFIX}/notes", json={**body, "save_requested_by_user": True})
    assert response.status_code == 404 and response.json()["code"] == "EXPLANATION_NOT_FOUND"
    assert client.post(f"{PREFIX}/notes", json={**body, "explanation_snapshot": {}}
                       ).status_code == 422
    request = fixture_request(ROOT)
    request["source"]["verification_status"] = "GITHUB_SOURCE_VERIFIED"
    assert client.post(f"{PREFIX}/learning/explain", json=request).status_code == 422
    assert client.get(f"{PREFIX}/notes").json()["notes"] == []


def test_snapshot_survives_changes_and_a_fresh_process(service, tmp_path):
    answer = explain(service)
    expected = deepcopy(answer)
    note = service.save_note(answer["grounded_explanation_id"], "First", "我的文字", True)
    original_note = deepcopy(note)
    # Changes to return values, provider state and later versions never rewrite stored JSON.
    answer["document_context"]["file_hash"] = "0" * 64
    note["github_sources"][0]["commit_sha"] = "0" * 40
    service.document.fixture.document["pages"][0]["paragraphs"] = ["Changed document"]
    service.github.fixture.source["commit_sha"] = "1" * 40
    again = service.save_note(expected["grounded_explanation_id"], "Second", "第二份笔记", True)
    assert again["explanation_snapshot"] == expected
    assert again["note_id"] != original_note["note_id"]
    script = (
        "import json,sys; from pathlib import Path; "
        "from concept_to_code_learning.api import create_app; "
        "from fastapi.testclient import TestClient; "
        "from concept_to_code_learning.integration.providers import ProviderConfig; "
        "c=TestClient(create_app(Path(sys.argv[1]), provider_config=ProviderConfig())); "
        "print(json.dumps(c.get('/api/sprint-1/notes').json()['notes']))"
    )
    result = subprocess.run([sys.executable, "-c", script, str(tmp_path)],
                            capture_output=True, text=True, check=True)
    assert json.loads(result.stdout) == [again, original_note]


def test_legacy_api_and_rows_remain_unchanged_while_new_notes_are_written(tmp_path):
    fixture = FixtureTutor(ROOT)
    legacy = NoteStore(tmp_path, fixture.schemas)
    answer = fixture.explain(QUESTION, fixture.context(), "Beginner")
    legacy.remember(answer)
    old_note = legacy.save(answer["grounded_explanation_id"], "Legacy note", "DO NOT REWRITE")
    with closing(legacy.connect()) as db, db:
        before = db.execute("SELECT * FROM notes").fetchall()
    client = TestClient(create_app(tmp_path, provider_config=ProviderConfig()))
    response = client.post(f"{PREFIX}/learning/explain", json=fixture_request(ROOT)).json()
    client.post(f"{PREFIX}/notes", json={"grounded_explanation_id": response["grounded_explanation_id"],
                                      "title": "New", "save_requested_by_user": True})
    assert client.get("/api/notes").json()["notes"] == [old_note]
    validate_record("saved-note", old_note, load_schemas(ROOT))
    with closing(legacy.connect()) as db, db:
        assert db.execute("SELECT * FROM notes").fetchall() == before
    assert "file_hash" not in old_note["grounded_explanation"]["document_context"]
    with pytest.raises(SliceError):
        validate("saved-note", old_note, SCHEMAS)
    with pytest.raises(ValueError):
        validate_record("grounded-explanation", response, load_schemas(ROOT))


def test_failed_save_rolls_back_without_changing_old_notes(service):
    answer = explain(service)
    first = service.save_note(answer["grounded_explanation_id"], "First", "preserved", True)
    with closing(service.notes.storage.connect()) as db, db:
        db.execute("CREATE TRIGGER reject_note BEFORE INSERT ON sprint_notes "
                   "BEGIN SELECT RAISE(ABORT, 'simulated storage failure'); END")
    with pytest.raises(SliceError) as failure:
        service.save_note(answer["grounded_explanation_id"], "Second", "unsaved", True)
    assert failure.value.code == "NOTE_SAVE_FAILED"
    assert service.notes.list() == [first]


def test_failed_explanation_storage_is_not_success(service, monkeypatch):
    def fail():
        raise sqlite3.OperationalError("simulated unavailable storage")
    monkeypatch.setattr(service.notes.storage, "connect", fail)
    with pytest.raises(SliceError) as failure:
        explain(service)
    assert failure.value.code == "EXPLANATION_SAVE_FAILED"


def test_mismatched_note_snapshot_is_rejected(records):
    # HTTP/SQLite JSON values have independent fields even if the producer reused objects.
    note = json.loads(json.dumps(records["saved-note"]))
    note["explanation_snapshot"]["question"] = "different"
    with pytest.raises(SliceError):
        validate("saved-note", note, SCHEMAS)


@pytest.mark.parametrize("method,path", [("post", "/documents"),
                                        ("get", "/documents/example/slides/1")])
def test_real_document_seams_are_explicit_stubs(client, method, path):
    response = getattr(client, method)(PREFIX + path)
    assert response.status_code == 501
    assert response.json()["code"] == "PROVIDER_NOT_IMPLEMENTED"


def test_contract_loading_is_independent_of_a_gbk_default(project, monkeypatch):
    path = project / "schemas/sprint-1/document-context.schema.json"
    schema = json.loads(path.read_text(encoding="utf-8"))
    schema["title"] = "学习上下文"
    path.write_text(json.dumps(schema, ensure_ascii=False), encoding="utf-8")
    original = Path.open

    def gbk_default(self, mode="r", buffering=-1, encoding=None, errors=None, newline=None):
        if "b" not in mode and (encoding is None or encoding == "locale"):
            encoding = "gbk"
        return original(self, mode, buffering, encoding, errors, newline)

    monkeypatch.setattr(Path, "open", gbk_default)
    assert load_contracts(project)["document-context"]["title"] == "学习上下文"


def test_sprint_connections_are_closed_after_success_and_failure(tmp_path, monkeypatch, records):
    legacy = NoteStore(tmp_path, load_schemas(ROOT))
    connections = []

    def connect():
        db = sqlite3.connect(legacy.path)
        connections.append(db)
        return db

    monkeypatch.setattr(legacy, "connect", connect)
    notes = SnapshotNoteStore(legacy, SCHEMAS)
    answer = deepcopy(records["grounded-explanation"])
    notes.remember(answer)
    notes.save(answer["grounded_explanation_id"], "Title", "mine", True)
    assert len(notes.list()) == 1
    with pytest.raises(SliceError, match="Generate"):
        notes.save("missing", "Title", "mine", True)
    assert len(connections) == 5
    for db in connections:
        with pytest.raises(sqlite3.ProgrammingError, match="closed"):
            db.execute("SELECT 1")
