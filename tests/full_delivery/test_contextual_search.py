"""Contextual search regressions use controlled providers and synthetic documents."""

import pytest

from concept_to_code_learning.full_contracts import models as m
from concept_to_code_learning.full_learning.service import LearningService

from .conftest import activate, explain_body

PREFIX = "/api/learning/v1"


def test_generic_followup_keeps_history_after_selection_changes(client, providers):
    session = activate(client)
    first = client.post(PREFIX + "/explanations", json=explain_body(session)).json()
    text = "梯度下降 😀 reduces a loss."
    selected = "reduces a loss."
    changed = client.post(f'{PREFIX}/sessions/{session["session_id"]}/context', json={
        "document_id": "doc-PDF", "document_revision": 1, "unit_id": "unit-PDF",
        "expected_context_revision": session["context_revision"], "selected_text": selected,
        "selection_locator": {"spans": [{"block_id": "block-PDF", "start": text.index(selected),
                                          "end": len(text)}], "normalization": "exact"}}).json()
    response = client.post(PREFIX + "/explanations", json=explain_body(changed, question="给我看看代码例子"))
    assert response.status_code == 200, response.text
    assert providers.tutor.conversations[-1][0].explanation_id == first["explanation"]["explanation_id"]
    assert len(providers.sources.calls) == 2  # Old evidence belongs to another selection epoch.
    other = activate(client, "DOCX", session=changed)
    assert client.post(PREFIX + "/explanations", json=explain_body(other)).status_code == 200
    assert providers.tutor.conversations[-1] == []


def test_automatic_terms_are_not_limited_to_predefined_topics():
    scope = m.SourceScope(source_mode="public_search", network_authorized=True, auto_public_search=True)
    terms = ["mutual information", "entropy", "mutual_info_score"]
    query = LearningService.make_query(scope, terms, "LIVE")
    assert query.concept_terms == terms
    assert query.question == "mutual information entropy mutual_info_score"


def test_public_eponym_survives_possessive_normalization():
    from concept_to_code_learning.learning_concepts import public_terms

    assert public_terms(["Dijkstra's algorithm", "Bayes’ theorem", "Bellman-Ford", "api_key secret"]) == [
        "Dijkstra algorithm", "Bayes theorem", "Bellman-Ford"]
    assert public_terms(["Bayes’s theorem"]) == ["Bayes theorem"]


def test_ai_repository_and_file_hints_reach_discovery_only_in_scope(client, providers):
    original = providers.tutor.plan
    async def plan(*args):
        result = await original(*args)
        result.source_query = m.SourceQuery(mode="FIXTURE", query_id=m.uid(), question="gradient",
            concept_terms=["gradient"], status="PLANNED", repository_hints=["fixture/repo-b"],
            file_hints=["implementation.py"])
        return result
    providers.tutor.plan = plan
    session = activate(client)
    assert client.post(PREFIX + "/explanations", json=explain_body(session, scope={
        "source_mode": "public_search", "network_authorized": True, "auto_public_search": True})).status_code == 200
    assert providers.sources.calls[-1].repository_hints == ["fixture/repo-b"]
    assert providers.sources.calls[-1].file_hints == ["implementation.py"]
    assert client.post(PREFIX + "/explanations", json=explain_body(session)).status_code == 200
    assert providers.sources.calls[-1].repository_allowlist == ["fixture/repo-a"]
    assert providers.sources.calls[-1].repository_hints == []


def test_ai_topic_decision_refreshes_sources_outside_the_hint_catalog(client, providers):
    session = activate(client)
    first = client.post(PREFIX + "/explanations", json=explain_body(session)).json()
    original = providers.tutor.plan
    async def plan(*args):
        value = await original(*args)
        value.reuse_previous_sources = False
        value.concepts = ["mutual information"]
        return value
    providers.tutor.plan = plan
    response = client.post(PREFIX + "/explanations", json=explain_body(session,
        question="换一个主题，解释互信息的实际代码", continue_from=first["explanation"]["explanation_id"]))
    assert response.status_code == 200, response.text
    assert len(providers.sources.calls) == 2
    assert providers.sources.calls[-1].concept_terms == ["mutual information"]


@pytest.mark.parametrize("first_failure", ["citation", "malformed_json", "flat_citation"])
def test_invalid_model_citation_is_regenerated_against_the_same_evidence(client, first_failure):
    import asyncio
    import json

    import httpx

    from concept_to_code_learning.runtime.async_model import AsyncLocalModelAdapter
    from concept_to_code_learning.runtime.local_model import LocalModelConfig
    from concept_to_code_learning.tutor.full import GroundedTutorProvider
    async def scenario():
        context = m.DocumentContext.model_validate(activate(client)["context"])
        calls = []
        def handler(request):
            calls.append(json.loads(request.content))
            value = {"answer_sections": [{"title": "概念", "text": "梯度下降用于降低损失。"}],
                     "document_citations": [{"block_id": "B1"}], "comparison": None, "limitations": [],
                     "concept_code_links": ([{"concept": "梯度", "source_id": "invented", "reason": "Invalid test claim"}]
                                            if len(calls) == 1 else [])}
            if first_failure == "flat_citation":
                value = {"answer": "根据当前材料解释梯度。", "document_ids": ["B1"],
                         "source_notes": {"invented": "Invalid test claim"} if len(calls) == 1 else {}}
            content = "{broken JSON" if len(calls) == 1 and first_failure == "malformed_json" else json.dumps(value)
            return httpx.Response(200, json={"model": "test-model", "choices": [{
                "message": {"content": content}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 100, "completion_tokens": 50}})
        config = LocalModelConfig("http://127.0.0.1:12345/v1", "test-model")
        adapter = AsyncLocalModelAdapter(config, transport=httpx.MockTransport(handler))
        tutor = GroundedTutorProvider(adapter, config)
        plan = m.TeachingPlan(mode="LIVE", plan_id=m.uid(), question="解释梯度", level="University",
                              concepts=["梯度"], needs_code=False, status="READY")
        try:
            result = await tutor.explain(context, [], plan, [])
        finally:
            await tutor.close()
        assert len(calls) == 2 and result.code_source_ids == []
        assert result.metrics.input_tokens == 200 and result.metrics.output_tokens == 100
        assert calls[0]["messages"][1] == calls[1]["messages"][1]
        assert calls[0]["messages"][0] != calls[1]["messages"][0]
    asyncio.run(scenario())


@pytest.mark.parametrize("tail,valid", [('', True), ('"', True), ('}', True), ('[]', False),
                                      ('}' * 9, False), ('{}', False), ('more content', False)])
def test_model_json_boundary_noise_does_not_allow_extra_content(tail, valid):
    import asyncio
    import json
    from types import SimpleNamespace

    from concept_to_code_learning.full_learning.errors import LearningError
    from concept_to_code_learning.tutor.full import GroundedTutorProvider, TeachingOutput

    async def scenario():
        value = {"answer_sections": [{"title": "概念", "text": "合成材料讲解。"}],
                 "document_citations": [{"block_id": "B1"}]}
        async def generate(messages):
            return SimpleNamespace(ok=True, text=json.dumps(value) + tail)
        tutor = GroundedTutorProvider(SimpleNamespace(generate=generate))
        if valid:
            parsed, _ = await tutor._json("test", {}, TeachingOutput)
            assert parsed.answer_sections[0].text == "合成材料讲解。"
        else:
            with pytest.raises(LearningError, match="MODEL_OUTPUT_INVALID"):
                await tutor._json("test", {}, TeachingOutput)
    asyncio.run(scenario())


def test_compact_stream_previews_prose_but_not_nested_source_fields():
    from concept_to_code_learning.tutor.preview import preview_sections

    assert preview_sections('{"answer":"训练用\\nX', code=True) == [
        {"title": "代码怎么实现", "text": "训练用\nX"}]
    assert preview_sections('{"answer":"训练用X","source_notes":{"answer":"metadata"}}') == [
        {"title": "核心意思", "text": "训练用X"}]
    assert preview_sections('{"source_notes":{"answer":"metadata"},"answer":"真正的正文') == [
        {"title": "核心意思", "text": "真正的正文"}]
    assert preview_sections('{"source_notes":{"answer":"metadata"}}') == []


@pytest.mark.parametrize("literal_name", [False, True])
def test_readable_references_preserve_names_in_material_and_chatml_json(client, literal_name):
    import asyncio
    import json

    import httpx

    from concept_to_code_learning.runtime.async_model import AsyncLocalModelAdapter
    from concept_to_code_learning.runtime.local_model import LocalModelConfig
    from concept_to_code_learning.tutor.full import GroundedTutorProvider

    async def scenario():
        context = m.DocumentContext.model_validate(activate(client)["context"])
        if literal_name:
            context.relevant_context_blocks[0].text = "B1 是本段使用的变量。"
        text = "B1 中的概念与当前问题有关。"
        def handler(request):
            body = json.loads(request.content)
            # Model-server behavior: an unconfigured turn boundary leaks into JSON.
            content = json.dumps({"answer": text, "document_ids": ["B1"]})
            if "<|im_end|>" not in body.get("stop", []):
                content += "<|im_end|>"
            return httpx.Response(200, json={"model": "Qwen-fixture", "choices": [{
                "message": {"content": content}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 10}})
        config = LocalModelConfig("http://127.0.0.1:12345/v1", "Qwen-fixture")
        tutor = GroundedTutorProvider(AsyncLocalModelAdapter(config, transport=httpx.MockTransport(handler)), config)
        try:
            result = await tutor.explain(context, [], m.TeachingPlan(
                mode="FIXTURE", plan_id=m.uid(), question="解释原文", level="Beginner",
                concepts=["概念"], needs_code=False, status="READY"), [])
            assert result.answer_sections[0].text == (text if literal_name else text.replace("B1", "原文"))
            assert result.document_citations[0].quote == context.relevant_context_blocks[0].text
        finally:
            await tutor.close()
    asyncio.run(scenario())


def test_fenced_chatml_json_can_preview_without_publishing_metadata():
    from concept_to_code_learning.tutor.preview import preview_sections
    assert preview_sections('```json\n{"answer":"正在解释真实代码', code=True) == [
        {"title": "代码怎么实现", "text": "正在解释真实代码"}]
    assert preview_sections('```json\n{"source_notes":{"answer":"内部信息') == []


@pytest.mark.parametrize("with_source", [False, True])
def test_narrative_binds_only_the_frozen_input_evidence(client, with_source):
    import asyncio
    import json

    import httpx

    from concept_to_code_learning.runtime.async_model import AsyncLocalModelAdapter
    from concept_to_code_learning.runtime.local_model import LocalModelConfig
    from concept_to_code_learning.tutor.full import GroundedTutorProvider

    session = activate(client)
    original = client.post(PREFIX + "/explanations", json=explain_body(session)).json()
    sources = [m.CodeEvidence.model_validate(original["sources"][0])] if with_source else []
    context = m.DocumentContext.model_validate(session["context"])
    context.relevant_context_blocks.append(context.relevant_context_blocks[0].model_copy(update={
        "block_id": "body-after-heading", "text": "update(x) computes the next value."}))
    async def scenario():
        calls = []
        def handler(request):
            # This protocol asks for prose only. It does not ask the model to create IDs.
            messages = json.loads(request.content)["messages"]
            calls.append(messages)
            payload = json.loads(messages[-1]["content"])
            assert bool(payload.get("verified_sources")) == with_source
            if with_source:
                assert payload["verified_sources"][0]["code"] == sources[0].code_excerpt
            # A filename containing the symbol is not an explanation of that symbol.
            answer = "update_example.py 提供相关的代码示例。" if with_source and len(calls) == 1 else "update(x) 返回 x - 1。"
            return httpx.Response(200, json={"model": "test-model", "choices": [{
                "message": {"content": json.dumps({"answer": answer, "limitations": []})},
                "finish_reason": "stop"}], "usage": {"prompt_tokens": 10, "completion_tokens": 10}})
        config = LocalModelConfig("http://127.0.0.1:12345/v1", "test-model")
        tutor = GroundedTutorProvider(AsyncLocalModelAdapter(config, transport=httpx.MockTransport(handler)), config)
        try:
            result = await tutor.explain(context, sources, m.TeachingPlan(
                mode="FIXTURE", plan_id=m.uid(), question="解释实现", level="Source-code",
                concepts=["递减"], needs_code=with_source, status="READY"), [])
            assert result.code_source_ids == [source.source_id for source in sources]
            assert [block.code for block in result.example_blocks] == [source.code_excerpt for source in sources]
            assert result.document_citations[0].block_id == context.relevant_context_blocks[0].block_id
            assert result.document_citations[0].quote == context.relevant_context_blocks[0].text
            assert [citation.block_id for citation in result.document_citations] == [
                block.block_id for block in context.relevant_context_blocks]
            assert len(calls) == (2 if with_source else 1)
            if with_source:
                assert "模型没有展开解释找到的代码" in calls[1][0]["content"]
        finally:
            await tutor.close()
    asyncio.run(scenario())
