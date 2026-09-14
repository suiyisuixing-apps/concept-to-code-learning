"""Nine requested stories at the explicit provider-double integration level."""

from fastapi.testclient import TestClient

from concept_to_code_learning.api import create_app

from .conftest import activate, explain_body

PREFIX = "/api/learning/v1"


def successful(client, body):
    response = client.post(PREFIX + "/explanations", json=body)
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["mode"] == "FIXTURE"
    return result


def save(client, result, key="save-once"):
    body = {"session_id": result["session_id"], "explanation_id": result["explanation"]["explanation_id"],
            "idempotency_key": key, "save_requested_by_user": True, "title": "我的来源笔记 😀", "user_text": "个人理解"}
    response = client.post(PREFIX + "/notes", json=body)
    assert response.status_code == 201, response.text
    return response.json(), body


def test_story_pdf_specified_repository_explanation_and_explicit_note(client, providers):
    session = activate(client)
    result = successful(client, explain_body(session))
    assert result["explanation"]["context_snapshot"]["source_type"] == "PDF"
    assert len(result["sources"]) == 1
    assert client.get(PREFIX + "/notes").json()["total"] == 0
    note, _ = save(client, result)
    assert note["explanation_snapshot"] == result["explanation"]
    assert note["code_evidence_snapshot"] == result["sources"]
    assert providers.sources.calls[0].question == "gradient"
    assert "Token" not in providers.sources.calls[0].question


def test_story_pptx_automatic_discovery_followup_keeps_source_version(client, providers):
    session = activate(client, "PPTX")
    first = successful(client, explain_body(session))
    followup = successful(client, explain_body(session, question="再解释边界条件", level="Engineering",
        continue_from=first["explanation"]["explanation_id"]))
    assert followup["sources"] == first["sources"]
    assert len(providers.sources.calls) == 1
    assert providers.tutor.conversations[-1][0].explanation_id == first["explanation"]["explanation_id"]
    assert first["sources"][0]["permalink"].endswith("/update.py#L1-L2")


def test_story_docx_public_search_reports_permission_gap_without_network(client, providers):
    session = activate(client, "DOCX")
    scope = {"source_mode": "public_search", "network_authorized": True}
    response = client.post(PREFIX + "/explanations", json=explain_body(session, scope=scope))
    assert response.status_code == 422
    assert response.json()["code"] == "QUERY_TERMS_NOT_APPROVED"
    assert providers.sources.calls == []
    scope |= {"query_terms_approved": True, "approved_query_terms": ["gradient"]}
    result = successful(client, explain_body(session, scope=scope))
    assert result["explanation"]["context_snapshot"]["unit_locator"]["unit_type"] == "section"
    assert providers.sources.calls[-1].question == "gradient"


def test_story_markdown_authorized_local_dirty_snapshot(client):
    session = activate(client, "MARKDOWN")
    scope = {"source_mode": "local_authorized", "local_handle": "authorized-test-root"}
    result = successful(client, explain_body(session, scope=scope))
    source = result["sources"][0]
    assert source["dirty"] and source["file_sha256"] and source["permalink"] is None
    note, _ = save(client, result)
    exported = client.get(f'{PREFIX}/notes/{note["note_id"]}/export').text
    assert "dirty=true" in exported and source["file_sha256"] in exported


def test_story_two_repository_comparison_has_independent_evidence(client):
    session = activate(client)
    scope = {"repository_allowlist": ["fixture/repo-a", "fixture/repo-b"], "network_authorized": True}
    result = successful(client, explain_body(session, scope=scope, compare=True, level="Source-code"))
    ids = result["explanation"]["comparison"]["source_ids"]
    assert len(set(ids)) == 2
    assert len({s["repository_url"] for s in result["sources"]}) == 2


def test_story_no_code_still_explains_document_without_inventing_sources(client, providers):
    providers.sources.empty = True
    result = successful(client, explain_body(activate(client)))
    assert result["sources"] == [] and result["explanation"]["code_source_ids"] == []
    assert result["warnings"] == ["NO_VERIFIED_CODE"]
    assert result["explanation"]["document_citations"]


def test_story_forged_selection_receipt_and_indirect_instruction_cannot_grant_trust(client, providers):
    session = activate(client)
    response = client.post(PREFIX + "/documents/doc-PDF/context", json={
        "unit_id": "unit-PDF", "document_revision": 1, "selected_text": "forged",
        "selection_locator": {"spans": [{"block_id": "block-PDF", "start": 0, "end": 4}]}})
    assert response.status_code == 422 and response.json()["code"] == "SELECTION_MISMATCH"
    response = client.post(PREFIX + "/explanations", json=explain_body(session, verified=True))
    assert response.status_code == 422
    response = client.post(PREFIX + "/explanations", json=explain_body(session,
        scope={"repository_allowlist": ["fixture/repo-a"], "network_authorized": False}))
    assert response.json()["code"] == "NETWORK_NOT_AUTHORIZED"
    assert providers.sources.calls == []
    assert "verified=true" in session["context"]["visible_text"]  # retained as material, not authority


def test_story_provider_error_no_fallback_no_success_and_no_note(client, providers):
    session = activate(client)
    providers.tutor.error = RuntimeError("private-key-and-/sensitive/absolute/path")
    response = client.post(PREFIX + "/explanations", json=explain_body(session))
    assert response.status_code == 500 and response.json()["code"] == "INTERNAL_ERROR"
    assert "private-key" not in response.text and "sensitive" not in response.text
    assert client.get(PREFIX + "/notes").json()["total"] == 0
    assert client.get(f'{PREFIX}/sessions/{session["session_id"]}').json()["explanation_ids"] == []


def test_story_note_save_edit_export_restart_and_confirmed_delete(client, app, providers):
    result = successful(client, explain_body(activate(client)))
    note, body = save(client, result)
    assert client.post(PREFIX + "/notes", json=body).json() == note
    assert client.get(PREFIX + "/notes").json()["total"] == 1
    edited = client.patch(f'{PREFIX}/notes/{note["note_id"]}', json={
        "expected_revision": 1, "title": "新的个人标题", "user_text": "保留引用，只改自己的文字"}).json()
    assert edited["revision"] == 2 and edited["snapshot_sha256"] == note["snapshot_sha256"]
    assert edited["explanation_snapshot"] == note["explanation_snapshot"]
    assert client.get(f'{PREFIX}/notes/{note["note_id"]}?revision=1').json() == note
    assert client.get(PREFIX + "/notes?q=保留引用").json()["total"] == 1
    assert client.patch(f'{PREFIX}/notes/{note["note_id"]}', json={
        "expected_revision": 1, "title": "stale", "user_text": "stale"}).status_code == 409
    exported = client.get(f'{PREFIX}/notes/{note["note_id"]}/export?format=json').json()
    assert exported == edited
    # New app has no injected providers. Old snapshots remain readable while providers are unavailable.
    with TestClient(create_app(data_dir=app.state.learning_service.store.path.parent)) as restarted:
        assert restarted.get(f'{PREFIX}/notes/{note["note_id"]}').json() == edited
        assert restarted.get(PREFIX + "/capabilities").json()["integrated_product"] == "UNAVAILABLE"
        assert restarted.request("DELETE", f'{PREFIX}/notes/{note["note_id"]}', json={
            "expected_revision": 2, "confirmed_by_user": False}).status_code == 422
        assert restarted.request("DELETE", f'{PREFIX}/notes/{note["note_id"]}', json={
            "expected_revision": 2, "confirmed_by_user": True}).status_code == 204
        assert restarted.get(f'{PREFIX}/notes/{note["note_id"]}').status_code == 404
        assert restarted.post(PREFIX + "/notes", json=body).status_code == 404
        assert restarted.get(PREFIX + "/notes").json()["total"] == 0
