import copy
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from concept_to_code_learning.api import create_app
from concept_to_code_learning.contracts import SCHEMA_NAMES, load_schemas, validate_record
from concept_to_code_learning.tutor.fixture import LEVELS, QUESTION, FixtureTutor

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def client(tmp_path):
    return TestClient(create_app(tmp_path))


def request(client, page=1, selected="", **overrides):
    body = {"question": QUESTION, "document_context": FixtureTutor(ROOT).context(page, selected),
            "explanation_level": "Beginner", **overrides}
    return client.post("/api/learning/explain", json=body)


def test_all_six_active_schemas_are_local_and_valid():
    assert tuple(load_schemas(ROOT)) == SCHEMA_NAMES


@pytest.mark.parametrize("level", LEVELS)
def test_grounded_answers_match_contract_and_do_not_claim_runtime(client, level):
    response = request(client, explanation_level=level)
    assert response.status_code == 200
    answer = response.json()
    validate_record("grounded-explanation", answer, load_schemas(ROOT))
    assert answer["mode"] == "FIXTURE"
    assert answer["status"] == "SCAFFOLD_DEMO"
    assert answer["runnable_example_status"] == "NOT_RUN"
    assert answer["code_comparison"] == []
    assert answer["github_sources"][0]["line_start"] == 12
    assert answer["github_sources"][0]["license_name"] == "MIT"
    assert client.get("/api/notes").json()["notes"] == []


def test_context_selection_and_page_are_bound_to_actual_fixture(client):
    tutor = FixtureTutor(ROOT)
    selected = tutor.document["pages"][1]["paragraphs"][0]
    answer = request(client, 2, selected).json()
    assert answer["document_citations"][0]["quote"] == selected
    assert answer["document_citations"][0]["page"] == 2
    assert request(client, 1, selected).status_code == 422
    body = {"question": QUESTION, "explanation_level": "Beginner",
            "document_context": tutor.context()}
    for field, value in [("file_name", "private.pdf"), ("current_page", 900),
                         ("selected_text_hash", "0" * 64), ("document_id", "forged")]:
        invalid = copy.deepcopy(body)
        invalid["document_context"][field] = value
        assert client.post("/api/learning/explain", json=invalid).status_code == 422
    assert request(client, question="Invent a repository for quantum chemistry").status_code == 422


def test_save_is_explicit_persistent_append_only_and_preserves_sources(tmp_path):
    client = TestClient(create_app(tmp_path))
    answer = request(client).json()
    body = {"grounded_explanation_id": answer["grounded_explanation_id"],
            "title": "My learning", "user_text": "MY OWN WORDS", "save_requested_by_user": False}
    assert client.post("/api/notes", json=body).status_code == 422
    body["save_requested_by_user"] = True
    first = client.post("/api/notes", json=body)
    assert first.status_code == 201
    first = first.json()
    second = client.post("/api/notes", json={**body, "user_text": "SECOND NOTE"}).json()
    assert second["note_id"] != first["note_id"]
    reopened = TestClient(create_app(tmp_path))
    assert reopened.get("/api/notes").json()["notes"] == [second, first]
    assert first["document_sources"] == answer["document_citations"]
    assert first["github_sources"] == answer["github_sources"]
    assert first["grounded_explanation"] == answer
    assert first["user_text"] == "MY OWN WORDS"
    assert first["created_at"] == first["updated_at"]
    assert reopened.put(f"/api/notes/{first['note_id']}", json=body).status_code in (404, 405)
    assert reopened.post("/api/notes", json={**body, "github_sources": []}).status_code == 422
    assert reopened.post("/api/notes", json={**body, "grounded_explanation_id": "missing"}
                         ).status_code == 404
    # Asking another question never mutates or creates personal notes.
    assert request(reopened, explanation_level="Engineering").status_code == 200
    assert reopened.get("/api/notes").json()["notes"] == [second, first]


@pytest.mark.parametrize("endpoint", ["search", "verify"])
def test_stubs_never_return_invented_results(client, endpoint):
    response = client.post(f"/api/github/{endpoint}", json={"query": "FastAPI"})
    assert response.status_code == 501
    assert response.json()["code"] == "NOT_IMPLEMENTED"
    assert response.json()["results"] == []
    assert response.json()["verification_status"] == "NEEDS_CONFIRMATION"


def test_status_and_execution_claims_fail_closed():
    schemas = load_schemas(ROOT)
    source = FixtureTutor(ROOT).source
    for field, value in [("verification_status", "VERIFIED"), ("commit_sha", "main"),
                         ("line_end", 11), ("license_url", None),
                         ("retrieved_at", "yesterday"), ("source_status", "AI_GENERATED")]:
        with pytest.raises(ValueError, match="INVALID_CONTRACT"):
            validate_record("github-code-source", {**source, field: value}, schemas)
    runnable = {"example_id": "test", "provenance": "AI_GENERATED", "source_ids": [],
                "status": "NOT_RUN", "command": None, "exit_code": None, "stdout": None,
                "stderr": None, "executed_at": None, "isolation": None}
    validate_record("runnable-example", runnable, schemas)
    with pytest.raises(ValueError, match="INVALID_CONTRACT"):
        validate_record("runnable-example", {**runnable, "status": "VERIFIED_RUNNABLE"}, schemas)


def test_health_is_truthful_and_dns_rebinding_host_is_rejected(client):
    assert client.get("/health").json()["mode"] == "FIXTURE"
    assert client.get("/api/demo/session").json()["capabilities"]["local_model"] is False
    assert client.get("/api/notes", headers={"host": "attacker.example"}).status_code == 400
