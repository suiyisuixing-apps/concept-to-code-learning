"""UTF-8 files must survive a non-UTF-8 process default, including pathlib's locale sentinel."""

import io
import json
import sys

import pytest

from concept_to_code_learning.cli import main
from concept_to_code_learning.contracts import load_schemas
from concept_to_code_learning.tutor.fixture import FixtureTutor


@pytest.fixture
def gbk_default(monkeypatch, tmp_path):
    original = io.open

    def open_gbk(file, mode="r", buffering=-1, encoding=None, errors=None,
                 newline=None, closefd=True, opener=None):
        if "b" not in mode and encoding in (None, "locale"):
            encoding = "gbk"
        return original(file, mode, buffering, encoding, errors, newline, closefd, opener)

    monkeypatch.setattr(io, "open", open_gbk)
    # Positive and negative controls prove the simulator catches implicit defaults.
    control = tmp_path / "control.txt"
    text = "中文来源 🚀"
    control.write_bytes(text.encode("utf-8"))
    assert control.read_text(encoding="utf-8") == text
    # Under PEP 686 UTF-8 mode, pathlib resolves an implicit/"locale" default to
    # UTF-8 before io.open is reached, so a GBK default cannot be simulated this
    # way. The explicit-encoding assertions below still run in both modes.
    if not sys.flags.utf8_mode:
        for encoding in (None, "locale"):
            with pytest.raises(UnicodeDecodeError):
                control.read_text(encoding=encoding)


def test_fixture_and_schema_loading_ignore_gbk_default(project, gbk_default):
    schema_path = project / "schemas/document-context.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    schema["description"] = "中文文档与选区 🚀"
    schema_path.write_text(json.dumps(schema, ensure_ascii=False), encoding="utf-8")
    assert load_schemas(project)["document-context"]["description"] == schema["description"]
    tutor = FixtureTutor(project)
    assert tutor.context()["document_id"] == tutor.document["document_id"]


def test_cli_demo_writes_utf8_json_with_a_gbk_default(project, gbk_default, monkeypatch):
    original = FixtureTutor.explain

    def explain_unicode(self, *args, **kwargs):
        answer = original(self, *args, **kwargs)
        answer["explanation"] += " 中文笔记 🚀"
        return answer

    monkeypatch.setattr(FixtureTutor, "explain", explain_unicode)
    monkeypatch.chdir(project)
    assert main(["demo"]) == 0
    for filename in ("grounded-explanation.json", "saved-note.json"):
        text = (project / "reports/learning-demo" / filename).read_bytes().decode("utf-8")
        assert "中文笔记 🚀" in text
        json.loads(text)
