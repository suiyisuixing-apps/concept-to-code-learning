"""Controlled GitHub/model doubles. External acceptance is recorded separately."""

import asyncio
import hashlib
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from concept_to_code_learning.api import create_app
from concept_to_code_learning.full_contracts import models as m
from concept_to_code_learning.full_learning.context import resolve_context
from concept_to_code_learning.full_learning.errors import LearningError
from concept_to_code_learning.repositories.library import RepositoryLibrary, chunks, repository_name
from concept_to_code_learning.repositories.models import AddRepository
from concept_to_code_learning.tutor.full import GroundedTutorProvider

ROOT = Path(__file__).resolve().parents[2]
COMMIT = "a" * 40
MIT = b"Permission is hereby granted, free of charge. THE SOFTWARE IS PROVIDED AS IS."


def blob(raw):
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


class GitHubDouble:
    def __init__(self, *, truncated=False):
        self.files = {"LICENSE": MIT, "src/main.py": b"from src.maths import square\n\ndef result(x):\n    return square(x)\n",
                      "src/maths.py": "# 中文 😀\ndef square(x):\n    return x * x\n".encode(),
                      "image.png": b"\x89PNG\0\0", "empty.txt": b""}
        self.truncated, self.reads, self.tree_reads = truncated, [], []
        self.closed = False
        self.mutation = None

    async def repository(self, owner, name):
        return {"full_name": "fixture/code", "default_branch": "main", "private": False, "description": "Controlled test repository"}

    async def resolve_ref(self, owner, name, ref):
        return COMMIT

    async def tree(self, owner, name, sha, *, recursive=True):
        self.tree_reads.append((sha, recursive))
        items = [{"path": p, "mode": "100644", "type": "blob", "size": len(raw), "sha": blob(raw)} for p, raw in self.files.items()]
        folder = {"path": "src", "mode": "040000", "type": "tree", "sha": "b" * 40}
        items += [{"path": "link.py", "mode": "120000", "type": "blob", "size": 7, "sha": "c" * 40},
                  {"path": "vendor", "mode": "160000", "type": "commit", "sha": "d" * 40},
                  {"path": "huge.py", "mode": "100644", "type": "blob", "size": 2 * 1024 * 1024, "sha": "e" * 40}]
        if not recursive:
            if sha == "b" * 40:
                items = [{**item, "path": item["path"].removeprefix("src/")} for item in items if item["path"].startswith("src/")]
            else:
                items = [item for item in items if "/" not in item["path"]] + [folder]
        else:
            items += [folder]
        return {"sha": sha if sha == "b" * 40 else "f" * 40, "tree": items, "truncated": self.truncated and recursive}

    async def fetch_raw(self, owner, name, commit, path):
        self.reads.append((commit, path))
        return self.mutation if self.mutation is not None and path == "src/main.py" else self.files[path]

    async def close(self):
        self.closed = True


def run(coro):
    return asyncio.run(coro)


def make_library(tmp_path, **kwargs):
    client = GitHubDouble(**kwargs)
    library = RepositoryLibrary(tmp_path / "中文 code 数据", client)
    repo = run(library.add(AddRepository(repository="fixture/code")))
    return library, client, repo


@pytest.mark.parametrize("value", ["fixture/code", "https://github.com/fixture/code", "github.com/fixture/code/", "https://github.com/fixture/code.git"])
def test_repository_addresses(value):
    assert repository_name(value) == "fixture/code"


@pytest.mark.parametrize("value", ["https://attacker.test/fixture/code", "http://github.com/fixture/code", "https://token@github.com/fixture/code",
                                    "https://github.com/fixture/code?token=secret", "https://github.com/fixture/code/tree/main", "../code", "a/b\n/c"])
def test_repository_address_boundary(value):
    with pytest.raises(LearningError):
        repository_name(value)


def test_tree_preserves_all_kinds_without_fetching_files(tmp_path):
    library, client, repo = make_library(tmp_path)
    page = run(library.tree(repo.repository_id))
    assert {item.kind for item in page.entries} == {"file", "folder", "symlink", "submodule"}
    assert client.reads == []
    assert repo.commit_sha == COMMIT and repo.complete_tree
    assert run(library.add(AddRepository(repository="fixture/code"))).repository_id == repo.repository_id
    assert len(library.list()) == 1
    found = run(library.tree(repo.repository_id, query="maths"))
    assert [e.path for e in found.entries] == ["src/maths.py"]


def test_truncated_tree_expands_by_verified_subtree_without_recursive_flag(tmp_path):
    library, client, repo = make_library(tmp_path, truncated=True)
    assert not repo.complete_tree
    assert client.tree_reads == [(COMMIT, True), (COMMIT, False)]
    page = run(library.tree(repo.repository_id, "src"))
    assert {e.path for e in page.entries} == {"src/main.py", "src/maths.py"}
    assert client.tree_reads[-1] == ("b" * 40, False)
    run(library.tree(repo.repository_id, "src"))
    assert len(client.tree_reads) == 3
    file = run(library.open_file(repo.repository_id, "src/main.py"))
    assert file.document.code_license.code_display_allowed


@pytest.mark.parametrize("path", ["link.py", "vendor", "huge.py", "../LICENSE", "/etc/passwd", "src/../../LICENSE", "src\\main.py", "src//main.py"])
def test_unsafe_or_unsupported_entries_do_not_fetch(tmp_path, path):
    library, client, repo = make_library(tmp_path)
    with pytest.raises(LearningError):
        run(library.open_file(repo.repository_id, path))
    assert not client.reads


def test_bytes_bind_to_tree_and_failure_does_not_persist_file(tmp_path):
    library, client, repo = make_library(tmp_path)
    client.mutation = b"print('substituted')"
    with pytest.raises(LearningError, match="SOURCE_MISMATCH"):
        run(library.open_file(repo.repository_id, "src/main.py"))
    with pytest.raises(LearningError, match="FILE_NOT_FOUND"):
        library.document("code-" + m.digest(repo.repository_id + ":src/main.py")[:40])


def test_file_and_real_import_are_frozen_and_survive_restart_without_network(tmp_path):
    library, client, repo = make_library(tmp_path)
    value = run(library.open_file(repo.repository_id, "src/main.py"))
    assert value.document.source_type == "CODE"
    assert value.document.original_sha256 == hashlib.sha256(client.files["src/main.py"]).hexdigest()
    assert value.units[0].supporting_blocks[0].code_location.file_path == "src/maths.py"
    assert value.units[0].supporting_blocks[0].code_license.files[0].content_sha256 == hashlib.sha256(MIT).hexdigest()
    assert all(commit == COMMIT for commit, _ in client.reads)
    restarted = RepositoryLibrary(library.path.parent, None)
    assert run(restarted.open_file(repo.repository_id, "src/main.py")) == value
    assert restarted.list()[0] == repo


def test_unicode_selection_and_related_file_citations_use_server_bytes(tmp_path):
    library, _, repo = make_library(tmp_path)
    value = run(library.open_file(repo.repository_id, "src/maths.py"))
    unit = value.units[0]
    block = unit.blocks[0]
    selection = "中文 😀"
    start = block.text.index(selection)
    request = m.ContextRequest(document_revision=1, unit_id=unit.unit_id, selected_text=selection,
        selected_text_hash=m.digest(selection), selection_locator=m.SelectionLocator(spans=[m.SelectionSpan(block_id=block.block_id, start=start, end=start+len(selection))]))
    context = resolve_context(value.document, unit, request)
    assert context.selected_text == selection and context.code_location.file_path == "src/maths.py"
    request.selected_text = "forged"
    with pytest.raises(LearningError, match="SELECTION_MISMATCH"):
        resolve_context(value.document, unit, request)


def test_chunking_keeps_last_line_and_numbering():
    text = "\r\n".join(f"# 行 {i} 😀" for i in range(610))
    pages = chunks(text)
    assert [start for start, _ in pages] == [1, 241, 481]
    assert "\n".join(body for _, body in pages) == text.replace("\r\n", "\n")
    with pytest.raises(LearningError, match="FILE_TOO_LARGE"):
        chunks("x" * 16001)


def test_license_and_binary_empty_states(tmp_path):
    library, client, repo = make_library(tmp_path)
    with pytest.raises(LearningError, match="UNSUPPORTED_FORMAT"):
        run(library.open_file(repo.repository_id, "image.png"))
    empty = run(library.open_file(repo.repository_id, "empty.txt"))
    assert empty.document.import_status == "NO_EXTRACTABLE_TEXT"
    assert empty.units[0].blocks[0].text == ""
    other = tmp_path / "unknown"
    fake = GitHubDouble()
    del fake.files["LICENSE"]
    unknown = RepositoryLibrary(other, fake)
    record = run(unknown.add(AddRepository(repository="fixture/code")))
    with pytest.raises(LearningError, match="LICENSE_UNKNOWN"):
        run(unknown.open_file(record.repository_id, "src/main.py"))
    assert not fake.reads


def test_code_plan_has_no_search_generation_and_packed_files_have_real_coordinates(tmp_path):
    library, _, repo = make_library(tmp_path)
    value = run(library.open_file(repo.repository_id, "src/main.py"))
    context = resolve_context(value.document, value.units[0], m.ContextRequest(document_revision=1, unit_id=value.units[0].unit_id))
    tutor = GroundedTutorProvider(None)
    plan = run(tutor.plan(context, "这段代码背后的知识是什么？", "Beginner", []))
    assert plan.source_query is None and plan.needs_code
    packed, _ = tutor.pack_context(context)
    assert [item["location"]["file_path"] for item in packed] == ["src/main.py", "src/maths.py"]
    assert all(item["location"]["commit_sha"] == COMMIT for item in packed)
    assert packed[1]["definitions"][0] == {"symbol": "square", "line_start": 2, "line_end": 3}


def test_code_sessions_annotations_notes_and_legacy_snapshots(tmp_path, providers):
    library, _, repo = make_library(tmp_path)
    app = create_app(tmp_path / "api-data", root=ROOT, full_providers=providers, repository_library=library)
    with TestClient(app) as client:
        prefix = "/api/learning/v1"
        opened = client.post(f"{prefix}/repositories/{repo.repository_id}/files", params={"path": "src/main.py"})
        assert opened.status_code == 200, opened.text
        value = opened.json()
        document, unit = value["document"], value["units"][0]
        session = client.post(prefix + "/sessions").json()
        body = {"document_id": document["document_id"], "document_revision": 1, "unit_id": unit["unit_id"], "expected_context_revision": 0}
        active = client.post(f"{prefix}/sessions/{session['session_id']}/context", json=body)
        assert active.status_code == 200, active.text
        assert len(active.json()["context"]["relevant_context_blocks"]) == 2
        assert client.get(f"{prefix}/documents/{document['document_id']}").json()["source_type"] == "CODE"
        text = unit["blocks"][0]["text"]
        annotation = client.post(f"{prefix}/documents/{document['document_id']}/annotations", json={
            "annotation_id": "code-annotation", "document_revision": 1, "unit_id": unit["unit_id"], "selected_text": text[:4],
            "selected_text_hash": m.digest(text[:4]), "selection_locator": {"spans": [{"block_id": unit["blocks"][0]["block_id"], "start": 0, "end": 4}]}, "comment": "我的代码批注"})
        assert annotation.status_code == 201, annotation.text
        assert annotation.json()["anchor"]["source_type"] == "CODE"
        request = {"request_id": "code-explanation", "session_id": session["session_id"],
                   "context_revision": 1, "question": "解释 square 和 result", "level": "Beginner",
                   "scope": {"source_mode": "specified_public", "repository_allowlist": ["fixture/code"], "network_authorized": False}}
        explained = client.post(prefix + "/explanations", json=request)
        assert explained.status_code == 200, explained.text
        assert explained.json()["status"] == "COMPLETE"
        assert "NO_VERIFIED_CODE" not in explained.json()["warnings"]
        assert providers.sources.calls == []
        saved = client.post(prefix + "/notes", json={"session_id": session["session_id"],
            "explanation_id": explained.json()["explanation"]["explanation_id"], "idempotency_key": "code-save",
            "save_requested_by_user": True, "title": "平方函数", "user_text": "保留这份代码的依据。"})
        assert saved.status_code == 201, saved.text
        note = saved.json()
        assert client.get(f"{prefix}/notes/{note['note_id']}").json()["snapshot_sha256"] == note["snapshot_sha256"]
        exported = client.get(f"{prefix}/notes/{note['note_id']}/export?format=markdown")
        assert COMMIT in exported.text and "src/main.py" in exported.text and "固定版本许可" in exported.text
        # Additive defaults serialize exactly like the prior contract, preserving old hashes.
        old = providers.document.records["doc-PDF"].model_dump(mode="json")
        assert "code_location" not in old and "code_license" not in old
        serialized = json.dumps(old, sort_keys=True, ensure_ascii=False)
        assert json.dumps(m.DocumentRecord.model_validate_json(serialized).model_dump(mode="json"), sort_keys=True, ensure_ascii=False) == serialized
        assert client.get(prefix + "/documents").json()["documents"][0]["source_type"] == "PDF"


@pytest.mark.parametrize("mode", ["empty", "unavailable", "partial"])
def test_repository_search_distinguishes_unavailable_results_from_no_match(tmp_path, providers, mode):
    from concept_to_code_learning.github_intelligence.errors import SourceError

    library, double, _ = make_library(tmp_path)

    async def search(terms, limit):
        return [] if mode == "empty" else ["fixture/code", "fixture/unavailable"]

    async def repository(owner, name):
        if mode == "partial" and name == "code":
            return {"full_name": "fixture/code", "description": "Available repository"}
        raise SourceError("RATE_LIMITED", "repository", "GitHub 请求暂时受限，请稍后重试。", 429)

    double.search_repositories = search
    double.repository = repository
    app = create_app(tmp_path / "api", root=ROOT, full_providers=providers, repository_library=library)
    with TestClient(app) as client:
        response = client.get("/api/learning/v1/repositories/search", params={"q": "fixture"})
        if mode == "unavailable":
            assert response.status_code == 429
            assert response.json()["code"] == "RATE_LIMITED"
        else:
            assert response.status_code == 200
            assert [item["repository"] for item in response.json()] == ([] if mode == "empty" else ["fixture/code"])



def test_code_model_cannot_publish_invented_citation_ids(tmp_path):
    import httpx

    from concept_to_code_learning.runtime.async_model import AsyncLocalModelAdapter
    from concept_to_code_learning.runtime.local_model import LocalModelConfig

    library, _, repo = make_library(tmp_path)
    value = run(library.open_file(repo.repository_id, "src/main.py"))
    context = resolve_context(value.document, value.units[0], m.ContextRequest(document_revision=1, unit_id=value.units[0].unit_id))
    messages = []
    def handler(request):
        body = json.loads(request.content)
        messages.append(body)
        content = {"answer": "result 调用 square，计算 x * x。", "document_ids": ["B99"], "source_notes": {}}
        if len(messages) == 2:
            content = {"answer": "result 调用 square；square 返回 x * x，计算输入的平方。", "limitations": []}
        return httpx.Response(200, json={"model": "test-model", "choices": [{"message": {"content": json.dumps(content, ensure_ascii=False)}, "finish_reason": "stop"}], "usage": {"prompt_tokens": 100, "completion_tokens": 30}})

    async def scenario():
        config = LocalModelConfig("http://127.0.0.1:12345/v1", "test-model")
        tutor = GroundedTutorProvider(AsyncLocalModelAdapter(config, transport=httpx.MockTransport(handler)), config)
        try:
            plan = await tutor.plan(context, "解释 result 背后的知识", "Beginner", [])
            result = await tutor.explain(context, [], plan, [])
            assert result.status == "CODE_GROUNDED"
            assert len(messages) == 2 and result.metrics.input_tokens == 200
            assert "上一次未通过检查" in messages[1]["messages"][0]["content"]
            assert len(result.document_citations) == 2
            assert all(c.block_id != "B99" for c in result.document_citations)
        finally:
            await tutor.close()
    run(scenario())


def test_nested_callback_locations_are_not_attributed_to_outer_methods():
    from concept_to_code_learning.tutor.full import code_definitions
    text = "class V:\n    def relu(self):\n        def _backward():\n            self.grad += 1\n        return _backward\n    def backward(self):\n        pass"
    values = code_definitions(text, 11)
    assert {v["symbol"]: (v["line_start"], v["line_end"]) for v in values} == {
        "V": (11, 17), "V.relu": (12, 15), "V.relu._backward": (13, 14), "V.backward": (16, 17)}


def test_comparison_facts_distinguish_values_gradients_and_strict_boundaries():
    from concept_to_code_learning.tutor.full import comparison_facts
    facts = comparison_facts("self.grad += (out.data > 0) * out.grad\nx = 0 if self.data < 0 else self.data")
    assert {f["expression"]: (f["tested_value"], f["true_at_boundary"]) for f in facts} == {
        "out.data > 0": ("out.data", False), "self.data < 0": ("self.data", False)}
    assert comparison_facts("x = y >= 0")[0]["true_at_boundary"] is True
    assert comparison_facts("bad : syntax !") == []


def test_selecting_a_short_file_keeps_definitions_and_boundaries_in_context(tmp_path):
    library, client, repo = make_library(tmp_path)
    # Prepare a distinct fixture snapshot before import, preserving exact Git identities.
    client.files["src/maths.py"] = ("# surrounding context\n" * 60 + "def gate(x):\n    return x if x > 0 else 0\n").encode()
    fresh = RepositoryLibrary(tmp_path / "short-selection", client)
    repo = run(fresh.add(AddRepository(repository="fixture/code")))
    value = run(fresh.open_file(repo.repository_id, "src/maths.py"))
    block = value.units[0].blocks[0]
    start = block.text.index("x > 0")
    context = resolve_context(value.document, value.units[0], m.ContextRequest(document_revision=1,
        unit_id=value.units[0].unit_id, selected_text="x > 0", selected_text_hash=m.digest("x > 0"),
        selection_locator=m.SelectionLocator(spans=[m.SelectionSpan(block_id=block.block_id, start=start, end=start + 5)])))
    packed, truncated = GroundedTutorProvider.pack_context(context)
    assert packed[0]["text"] == block.text and not truncated
    assert packed[0]["definitions"][0]["symbol"] == "gate"
    assert packed[0]["comparison_facts"][0]["true_at_boundary"] is False
