from fastapi.testclient import TestClient

from concept_to_code_learning.api import create_app
from concept_to_code_learning.full_contracts.models import digest

PREFIX = "/api/learning/v1"


def test_real_markdown_upload_navigation_selection_and_asset_boundary(tmp_path):
    with TestClient(create_app(tmp_path)) as client:
        uploaded = client.post(
            PREFIX + "/documents",
            params={"file_name": "中文 讲义.md"},
            content="# 标题\n选择 😀 文字".encode("utf-8"),
            headers={"Content-Type": "application/octet-stream"},
        )
        assert uploaded.status_code == 201
        record = uploaded.json()
        unit = client.get(f"{PREFIX}/documents/{record['document_id']}/units").json()["units"][0]
        source = unit["blocks"][0]["text"]
        selected = "😀"
        start = source.index(selected)
        context = client.post(
            f"{PREFIX}/documents/{record['document_id']}/context",
            json={
                "document_revision": record["revision"],
                "unit_id": unit["unit_id"],
                "selected_text": selected,
                "selected_text_hash": digest(selected),
                "selection_locator": {
                    "spans": [{"block_id": unit["blocks"][0]["block_id"], "start": start,
                               "end": start + 1}],
                    "normalization": "exact",
                },
            },
        )
        assert context.status_code == 200 and context.json()["selected_text"] == selected
        assert client.get(f"{PREFIX}/documents/{record['document_id']}/assets/not-an-id").status_code == 404


def test_api_rejects_corrupt_version_and_traversal(tmp_path):
    with TestClient(create_app(tmp_path)) as client:
        assert client.post(PREFIX + "/documents", params={"file_name": "../x.md"}, content=b"x").status_code == 422
        assert client.post(PREFIX + "/documents", params={"file_name": "x.pdf"}, content=b"not-pdf").json()["code"] == "INVALID_FILE"
        record = client.post(PREFIX + "/documents", params={"file_name": "x.md"}, content=b"text").json()
        unit = client.get(f"{PREFIX}/documents/{record['document_id']}/units").json()["units"][0]
        response = client.post(f"{PREFIX}/documents/{record['document_id']}/context", json={
            "document_revision": 2, "unit_id": unit["unit_id"], "selected_text": "",
        })
        assert response.status_code == 409 and response.json()["code"] == "DOCUMENT_VERSION_MISMATCH"
