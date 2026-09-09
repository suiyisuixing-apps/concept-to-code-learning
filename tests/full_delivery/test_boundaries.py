import asyncio
import json
import sqlite3
import threading
from concurrent.futures import ThreadPoolExecutor

import pytest
from conftest import activate, explain_body
from fastapi.testclient import TestClient

from concept_to_code_learning.api import create_app
from concept_to_code_learning.full_contracts import models as m
from concept_to_code_learning.full_learning.errors import LearningError
from concept_to_code_learning.full_learning.service import LearningService
from concept_to_code_learning.full_learning.store import LearningStore

PREFIX = "/api/learning/v1"


@pytest.mark.parametrize("level", ["Beginner", "University", "Engineering", "Source-code"])
def test_all_levels_use_same_versioned_pipeline(client, level):
    response = client.post(PREFIX + "/explanations", json=explain_body(activate(client), level=level))
    assert response.status_code == 200
    assert response.json()["explanation"]["level"] == level


def test_candidate_choice_is_bound_to_original_session_and_scope(client, providers):
    providers.sources.selection_required = True
    session = activate(client)
    body = explain_body(session)
    result = client.post(PREFIX + "/explanations", json=body).json()
    assert result["status"] == "NEEDS_SOURCE_SELECTION" and result["explanation"] is None
    assert client.get(PREFIX + "/notes").json()["total"] == 0
    chosen = {"query_id": result["query_id"], "candidate_ids": [result["candidates"][0]["candidate_id"]]}
    other = activate(client)
    rejected = client.post(PREFIX + "/explanations", json=explain_body(other, **chosen))
    assert rejected.status_code == 404 and rejected.json()["code"] == "SOURCE_MISMATCH"
    assert client.post(PREFIX + "/explanations", json=body | chosen).status_code == 200


@pytest.mark.parametrize("mutation", [
    lambda x: x.model_copy(update={"excerpt_sha256": "0" * 64}),
    lambda x: x.model_copy(update={"file_path": "../secret.py"}),
    lambda x: x.model_copy(update={"verification_checks": {"file": "PASSED"}}),
    lambda x: x.model_copy(update={"execution_status": "RUN_PASSED"}),
])
def test_invalid_provider_evidence_rejected_before_tutor_explanation(client, providers, mutation):
    providers.sources.mutate = mutation
    response = client.post(PREFIX + "/explanations", json=explain_body(activate(client)))
    assert response.status_code == 502
    assert providers.tutor.conversations == []
    assert client.get(PREFIX + "/notes").json()["total"] == 0


@pytest.mark.parametrize("mutation", [
    lambda x: x.model_copy(update={"code_source_ids": ["not-in-registry"]}),
    lambda x: x.model_copy(update={"unsupported_claims": ["unsupported fact"]}),
    lambda x: x.model_copy(update={"answer_sections": [m.AnswerSection(title="Bad", text="https://evil.example/")]}),
    lambda x: x.model_copy(update={"example_blocks": [x.example_blocks[0].model_copy(update={"code": "altered"})]}),
    lambda x: x.model_copy(update={"mode": "LIVE", "status": "GROUNDED"}),
])
def test_invalid_model_answer_is_not_relabelled_success(client, providers, mutation):
    providers.tutor.mutate = mutation
    session = activate(client)
    response = client.post(PREFIX + "/explanations", json=explain_body(session))
    assert response.status_code == 502
    assert client.get(f'{PREFIX}/sessions/{session["session_id"]}').json()["explanation_ids"] == []


def test_source_cache_hash_and_session_are_checked_on_every_id_read(client, app):
    first = activate(client)
    result = client.post(PREFIX + "/explanations", json=explain_body(first)).json()
    source_id = result["sources"][0]["source_id"]
    second = activate(client)
    assert client.get(f'{PREFIX}/sources/{source_id}', params={"session_id": second["session_id"]}).status_code == 404
    with app.state.learning_service.store.transaction() as db:
        db.execute("UPDATE fd_sources SET body=? WHERE id=?", ("{}", source_id))
    response = client.get(f'{PREFIX}/sources/{source_id}', params={"session_id": first["session_id"]})
    assert response.status_code == 409 and response.json()["code"] == "SOURCE_MISMATCH"


def test_revoked_local_handle_is_rechecked_before_candidate_verification(client, providers):
    session = activate(client)
    result = client.post(PREFIX + "/sources/search", json={
        "session_id": session["session_id"], "context_revision": session["context_revision"],
        "question": "解释梯度下降", "concept_terms": ["gradient"],
        "scope": {"source_mode": "local_authorized", "local_handle": "authorized-test-root"}}).json()

    async def revoked():
        return []

    providers.sources.local_handles = revoked
    response = client.post(PREFIX + "/sources/verify", json={
        "session_id": session["session_id"], "query_id": result["query_id"],
        "candidate_id": result["candidates"][0]["candidate_id"]})
    assert response.status_code == 403 and response.json()["code"] == "AUTH_REQUIRED"
    assert providers.sources.receipts == {}


@pytest.mark.parametrize("field", ["title", "concept", "reason", "example"])
def test_model_cannot_put_unverified_urls_in_other_rendered_prose(client, providers, field):
    def add_url(answer):
        if field == "title":
            answer.answer_sections[0].title = "https://invented.example/"
        elif field == "example":
            answer.example_blocks[0].explanation = "https://invented.example/"
        else:
            setattr(answer.concept_code_links[0], field, "https://invented.example/")
        return answer
    providers.tutor.mutate = add_url
    session = activate(client)
    response = client.post(PREFIX + "/explanations", json=explain_body(session))
    assert response.status_code == 502 and response.json()["code"] == "CITATION_INVALID"
    assert client.get(f'{PREFIX}/sessions/{session["session_id"]}').json()["explanation_ids"] == []


def test_invalid_document_response_has_safe_structured_error(client, providers):
    async def invalid(*args):
        return {"private": "/secret/user/document", "token": "do-not-echo"}
    providers.document.get_unit = invalid
    response = client.get(PREFIX + "/documents/doc-PDF/units/unit-PDF")
    assert response.status_code == 502 and response.json()["code"] == "INVALID_PROVIDER_RESPONSE"
    assert "do-not-echo" not in response.text and "/secret/user" not in response.text


def test_blank_page_is_readable_but_cannot_generate_fabricated_text(client, providers):
    providers.document.units["unit-PDF"].blocks = []
    providers.document.units["unit-PDF"].extraction_status = "NO_EXTRACTABLE_TEXT"
    session = activate(client)
    assert session["context"]["visible_text"] == "" and session["context"]["coverage"] == "NO_EXTRACTABLE_TEXT"
    response = client.post(PREFIX + "/explanations", json=explain_body(session))
    assert response.json()["code"] == "NO_EXTRACTABLE_TEXT" and providers.tutor.plan_count == 0


def test_precise_unicode_offsets_and_recorded_whitespace_normalization(client):
    original = "梯度下降 😀"
    response = client.post(PREFIX + "/documents/doc-PDF/context", json={
        "document_revision": 1, "unit_id": "unit-PDF", "selected_text": "梯度下降   😀",
        "selected_text_hash": m.digest(original),
        "selection_locator": {"normalization": "whitespace-v1", "spans": [
            {"block_id": "block-PDF", "start": 0, "end": len(original)}]}})
    assert response.status_code == 200
    assert response.json()["selected_text"] == original
    assert response.json()["selected_text_hash"] == m.digest(original)


def test_request_retries_do_not_generate_second_model_answer(client, providers):
    session = activate(client)
    body = explain_body(session, request_id="same-request")
    first = client.post(PREFIX + "/explanations", json=body)
    assert first.status_code == 200
    assert client.post(PREFIX + "/explanations", json=body).json() == first.json()
    assert providers.tutor.plan_count == 1
    assert client.post(PREFIX + "/explanations", json=body | {"question": "changed"}).status_code == 409


def test_origin_upload_limits_and_private_errors(client):
    assert client.post(PREFIX + "/sessions", headers={"Origin": "https://hostile.example"}).status_code == 403
    assert client.post(PREFIX + "/documents?file_name=../secret.pdf", content=b"x").status_code == 422
    assert client.post(PREFIX + "/documents?file_name=okay.pdf", content=b"x",
                       headers={"content-length": str(22 * 1024 * 1024)}).status_code == 413
    response = client.post(PREFIX + "/documents", params={"file_name": "中文.pdf"},
                           content=b"CONTROLLED-TRANSPORT-PROBE")
    assert response.status_code == 201
    invalid = client.post(PREFIX + "/notes", json={"secret": "do-not-echo"})
    assert invalid.status_code == 422 and "do-not-echo" not in invalid.text


def test_uninstalled_modules_report_partial_without_fixture_fallback(tmp_path):
    with TestClient(create_app(tmp_path)) as client:
        caps = client.get(PREFIX + "/capabilities").json()
        assert caps["integrated_product"] == "UNAVAILABLE" and caps["status"] == "PARTIAL"
        assert all(not caps[key]["available"] for key in ("document", "sources", "tutor"))
        assert caps["persistent_notes"] and caps["target_hardware"] == "NOT_TESTED"
        assert client.get("/api/sprint-1/session").status_code == 200


@pytest.mark.parametrize("action", ["cancel", "navigate"])
def test_cancellation_or_page_change_prevents_late_commit(tmp_path, providers, action):
    async def run():
        store = LearningStore(tmp_path)
        service = LearningService(providers, store)
        session = store.create_session()
        session = await service.activate(session.session_id, m.ActivateContext(document_id="doc-PDF",
            document_revision=1, unit_id="unit-PDF", expected_context_revision=0))
        request = m.ExplanationRequest.model_validate(explain_body(session.model_dump(mode="json")))
        providers.tutor.delay = True
        task = asyncio.create_task(service.explain(request))
        await asyncio.wait_for(providers.tutor.started.wait(), 2)
        if action == "cancel":
            await service.cancel(session.session_id, request.request_id)
        else:
            await service.activate(session.session_id, m.ActivateContext(document_id="doc-PPTX",
                document_revision=1, unit_id="unit-PPTX", expected_context_revision=1))
        providers.tutor.release.set()
        with pytest.raises(LearningError, match="CANCELLED"):
            await task
        assert store.session(session.session_id).explanation_ids == []
        assert store.list_notes()[1] == 0
        with store.transaction(write=False) as db:
            assert db.execute("SELECT count(*) FROM fd_explanations").fetchone()[0] == 0
        assert not service.active
        await service.close()
    asyncio.run(run())


def test_older_navigation_cannot_replace_later_context(tmp_path, providers):
    async def run():
        service = LearningService(providers, LearningStore(tmp_path))
        session = service.store.create_session()
        providers.document.delay_document = "doc-PDF"
        old = asyncio.create_task(service.activate(session.session_id, m.ActivateContext(
            document_id="doc-PDF", document_revision=1, unit_id="unit-PDF", expected_context_revision=0)))
        await providers.document.started.wait()
        latest = await service.activate(session.session_id, m.ActivateContext(document_id="doc-DOCX",
            document_revision=1, unit_id="unit-DOCX", expected_context_revision=0))
        providers.document.release.set()
        with pytest.raises(LearningError, match="CONTEXT_REVISION_CONFLICT"):
            await old
        assert service.store.session(session.session_id) == latest
    asyncio.run(run())


def test_transaction_failure_and_baseexception_close_connections_and_rollback(client, app, monkeypatch):
    store = app.state.learning_service.store
    result = client.post(PREFIX + "/explanations", json=explain_body(activate(client))).json()
    body = m.SaveNoteRequest(session_id=result["session_id"],
        explanation_id=result["explanation"]["explanation_id"], idempotency_key="fault-test",
        save_requested_by_user=True, title="不能留下半条笔记", user_text="内容")
    original = store.connect
    connections = []
    failure = sqlite3.OperationalError

    class Broken:
        def __init__(self):
            self.raw = original()
            connections.append(self.raw)
        def __enter__(self):
            self.raw.__enter__()
            return self
        def __exit__(self, *args):
            return self.raw.__exit__(*args)
        def close(self):
            self.raw.close()
        def execute(self, statement, parameters=()):
            result = self.raw.execute(statement, parameters)
            if statement.startswith("INSERT INTO fd_note_revisions"):
                raise failure()
            return result

    monkeypatch.setattr(store, "connect", Broken)
    with pytest.raises(LearningError, match="STORAGE_FAILURE"):
        store.save_note(body)
    failure = asyncio.CancelledError
    with pytest.raises(asyncio.CancelledError):
        store.save_note(body)
    for connection in connections:
        with pytest.raises(sqlite3.ProgrammingError):
            connection.execute("SELECT 1")
    monkeypatch.setattr(store, "connect", original)
    with store.transaction(write=False) as db:
        for table in ("fd_notes", "fd_note_revisions", "fd_save_keys"):
            assert db.execute("SELECT count(*) FROM " + table).fetchone()[0] == 0
    saved = store.save_note(body)
    assert saved.title == body.title


def test_new_store_does_not_touch_existing_legacy_file(tmp_path):
    old = tmp_path / "fixture-notes.sqlite3"
    original = "仅作为不可更改原件的合成测试文件 😀".encode()
    old.write_bytes(original)
    LearningStore(tmp_path)
    assert old.read_bytes() == original


def test_utc_dates_and_error_schema_do_not_leak_test_private_values(client):
    response = client.post(PREFIX + "/sessions").json()
    assert response["created_at"].endswith("Z")
    error = client.post(PREFIX + "/explanations", json={"session_id": "/private-path"}).json()
    assert set(m.LearningErrorResponse.model_fields) == set(error)
    assert "private-path" not in json.dumps(error)


def test_http_cancel_returns_cancelled_and_does_not_persist_answer(client, providers, app):
    session = activate(client)
    providers.tutor.delay = True
    providers.tutor.started = threading.Event()
    body = explain_body(session, request_id="http-cancel")
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(client.post, PREFIX + "/explanations", json=body)
        assert providers.tutor.started.wait(3)
        assert client.delete(PREFIX + "/requests/http-cancel", params={
            "session_id": session["session_id"]}).status_code == 204
        response = future.result(timeout=5)
    assert response.status_code == 409 and response.json()["code"] == "CANCELLED"
    assert not app.state.learning_service.active


def test_unknown_license_keeps_metadata_without_code_and_exports_it(client, providers):
    def unknown(source):
        return source.model_copy(update={"code_excerpt": "", "excerpt_sha256": m.digest(""),
            "license_observation": m.LicenseObservation(status="UNKNOWN", limitations=["No license observed"])})
    providers.sources.mutate = unknown
    result = client.post(PREFIX + "/explanations", json=explain_body(activate(client))).json()
    assert result["sources"] == [] and result["explanation"]["code_source_ids"] == []
    assert result["source_observations"][0]["code_excerpt"] == ""
    assert "LICENSE_UNKNOWN" in result["warnings"] and "NO_VERIFIED_CODE" in result["warnings"]
    note = client.post(PREFIX + "/notes", json={"session_id": result["session_id"],
        "explanation_id": result["explanation"]["explanation_id"], "idempotency_key": "unknown-license",
        "save_requested_by_user": True, "title": "metadata only", "user_text": ""}).json()
    exported = client.get(f'{PREFIX}/notes/{note["note_id"]}/export').text
    assert "UNKNOWN" in exported and "固定版本来源" in exported and "def update" not in exported


def test_concurrent_identical_saves_make_one_note(client, app):
    result = client.post(PREFIX + "/explanations", json=explain_body(activate(client))).json()
    body = m.SaveNoteRequest(session_id=result["session_id"],
        explanation_id=result["explanation"]["explanation_id"], idempotency_key="concurrent-save",
        title="same intent", user_text="same text", save_requested_by_user=True)
    store = app.state.learning_service.store
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda _: store.save_note(body), range(4)))
    assert len({note.note_id for note in results}) == 1
    assert store.list_notes()[1] == 1
