"""Annotations keep exact server-owned quotes and survive independently of AI sessions."""

import pytest

from concept_to_code_learning.full_contracts.models import digest
from concept_to_code_learning.full_learning.annotations import AnnotationStore

PREFIX = "/api/learning/v1"


def request(kind="MARKDOWN", **changes):
    return {"annotation_id": "annotation-test", "document_revision": 1, "unit_id": "unit-" + kind,
            "selected_text": "梯度下降 😀", "selected_text_hash": digest("梯度下降 😀"),
            "selection_locator": {"spans": [{"block_id": "block-" + kind, "start": 0, "end": 6}],
                                  "normalization": "exact"}, "comment": "为什么这样更新？我想用自己的话重写。", **changes}


@pytest.mark.parametrize("kind", ["PDF", "PPTX", "DOCX", "MARKDOWN"])
def test_save_quote_from_each_format_without_model_or_learning_session(client, providers, tmp_path, kind):
    response = client.post(f"{PREFIX}/documents/doc-{kind}/annotations", json=request(kind))
    assert response.status_code == 201, response.text
    saved = response.json()
    assert saved["anchor"]["selected_text"] == "梯度下降 😀"
    assert saved["anchor"]["original_sha256"] == digest(kind)
    assert saved["anchor"]["selected_text_hash"] == digest(saved["anchor"]["selected_text"])
    assert saved["mode"] == "FIXTURE" and saved["revision"] == 1
    assert not providers.sources.calls and providers.tutor.plan_count == 0
    again = AnnotationStore(tmp_path / "临时 数据")
    items, total = again.list("doc-" + kind, "unit-" + kind, 0, 50)
    assert total == 1 and items[0].model_dump(mode="json") == saved
    assert client.get(f"{PREFIX}/notes").json()["total"] == 0


@pytest.mark.parametrize("changes,code", [
    ({"selected_text": "伪造原文", "selected_text_hash": digest("伪造原文")}, "SELECTION_MISMATCH"),
    ({"selected_text_hash": "a" * 64}, "SELECTION_MISMATCH"),
    ({"document_revision": 2}, "DOCUMENT_VERSION_MISMATCH"),
    ({"selection_locator": {"spans": [{"block_id": "missing", "start": 0, "end": 2}]}}, "SELECTION_MISMATCH"),
    ({"selected_text": "", "selected_text_hash": None, "selection_locator": None}, "SELECTION_REQUIRED"),
    ({"comment": "   "}, "INVALID_REQUEST"),
])
def test_annotation_rejects_invalid_quote_revision_and_blank_comment(client, changes, code):
    result = client.post(f"{PREFIX}/documents/doc-MARKDOWN/annotations", json=request(**changes))
    assert result.status_code in {409, 422}
    assert result.json()["code"] == code
    assert client.get(f"{PREFIX}/documents/doc-MARKDOWN/annotations").json()["total"] == 0


def test_annotation_edit_keeps_anchor_and_rejects_lost_updates(client):
    original = client.post(f"{PREFIX}/documents/doc-MARKDOWN/annotations", json=request()).json()
    updated = client.patch(f"{PREFIX}/annotations/annotation-test", json={"expected_revision": 1, "comment": "我的新理解 😀"})
    assert updated.status_code == 200
    assert updated.json()["anchor"] == original["anchor"] and updated.json()["revision"] == 2
    stale = client.patch(f"{PREFIX}/annotations/annotation-test", json={"expected_revision": 1, "comment": "过期编辑"})
    assert stale.status_code == 409 and stale.json()["code"] == "ANNOTATION_REVISION_CONFLICT"
    tamper = client.patch(f"{PREFIX}/annotations/annotation-test", json={"expected_revision": 2, "comment": "修改", "anchor": {}})
    assert tamper.status_code == 422
    assert client.get(f"{PREFIX}/documents/doc-MARKDOWN/annotations").json()["annotations"][0]["comment"] == "我的新理解 😀"


def test_idempotent_save_delete_tombstone_and_location_pagination(client):
    route = f"{PREFIX}/documents/doc-MARKDOWN/annotations"
    one = client.post(route, json=request()).json()
    assert client.post(route, json=request()).json() == one
    assert client.post(route, json=request(comment="different")).status_code == 409
    client.post(route, json=request(annotation_id="annotation-second"))
    page = client.get(route + "?limit=1&offset=1&unit_id=unit-MARKDOWN").json()
    assert page["total"] == 2 and page["annotations"][0]["annotation_id"] == "annotation-test"
    assert client.get(route + "?unit_id=another-unit").json()["total"] == 0
    assert client.get(f"{PREFIX}/documents/doc-PDF/annotations").json()["total"] == 0
    delete_route = f"{PREFIX}/annotations/annotation-test"
    assert client.request("DELETE", delete_route, json={"expected_revision": 1, "confirmed_by_user": False}).status_code == 422
    assert client.request("DELETE", delete_route, json={"expected_revision": 2, "confirmed_by_user": True}).status_code == 409
    assert client.request("DELETE", delete_route, json={"expected_revision": 1, "confirmed_by_user": True}).status_code == 204
    assert client.post(route, json=request()).json()["code"] == "ANNOTATION_DELETED"
    assert client.get(route).json()["total"] == 1


def test_annotation_original_file_integrity_and_origin_boundary(client, providers):
    body = request()
    response = client.post(f"{PREFIX}/documents/doc-MARKDOWN/annotations", json=body, headers={"Origin": "https://untrusted.invalid"})
    assert response.status_code == 403
    providers.document.units["unit-MARKDOWN"].document_revision = 2
    response = client.post(f"{PREFIX}/documents/doc-MARKDOWN/annotations", json=body)
    assert response.status_code == 409 and response.json()["code"] == "DOCUMENT_VERSION_MISMATCH"
