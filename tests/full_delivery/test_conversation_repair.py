"""Incident regressions with isolated providers; no network or personal documents."""

import asyncio
import json

import httpx
import pytest
from conftest import activate, explain_body

from concept_to_code_learning.full_contracts import models as m
from concept_to_code_learning.full_learning.errors import LearningError
from concept_to_code_learning.full_learning.service import LearningService
from concept_to_code_learning.github_intelligence.verifier import excerpt
from concept_to_code_learning.learning_concepts import guide_for, guide_for_terms
from concept_to_code_learning.runtime.async_model import AsyncLocalModelAdapter
from concept_to_code_learning.runtime.local_model import LocalModelConfig
from concept_to_code_learning.tutor.catalog import TutorCatalog
from concept_to_code_learning.tutor.full import GroundedTutorProvider
from concept_to_code_learning.tutor.preview import preview_sections

PREFIX = "/api/learning/v1"


def test_empty_approved_terms_are_a_search_error_not_a_model_failure(client, providers):
    body = explain_body(activate(client), scope={"source_mode": "public_search",
        "network_authorized": True, "query_terms_approved": True, "approved_query_terms": []})
    response = client.post(PREFIX + "/explanations", json=body)
    assert response.status_code == 422 and response.json()["code"] == "QUERY_TERMS_NOT_APPROVED"
    assert providers.sources.calls == []


def test_automatic_search_transmits_only_public_vocabulary_and_still_needs_network():
    scope = m.SourceScope(source_mode="public_search", network_authorized=True, auto_public_search=True)
    query = LearningService.make_query(scope, ["predict", "PRIVATE_COURSE_2030", "target"], "LIVE")
    assert query.concept_terms == ["predict", "target"]
    assert query.approved_query_terms == query.concept_terms
    assert "PRIVATE" not in query.question
    assert not scope.query_terms_approved and not scope.approved_query_terms
    scope.network_authorized = False
    with pytest.raises(LearningError, match="NETWORK_NOT_AUTHORIZED"):
        LearningService.make_query(scope, ["predict"], "LIVE")


def test_streamed_results_keep_the_same_verified_contract_and_history(client):
    session = activate(client)
    response = client.post(PREFIX + "/explanations/stream", json=explain_body(session))
    events = [json.loads(line) for line in response.text.splitlines()]
    assert events[0] == {"type": "progress", "stage": "planning"}
    assert events[-1]["type"] == "result"
    result = m.ExplanationResult.model_validate(events[-1]["value"])
    assert result.explanation.code_source_ids and result.sources
    assert client.get(f'{PREFIX}/sessions/{session["session_id"]}/history').json() == [events[-1]["value"]]
    assert client.get(PREFIX + "/sessions/recent").json()["session_id"] == session["session_id"]
    assert client.get(PREFIX + "/notes").json()["total"] == 0


def test_stream_errors_never_publish_a_success_or_savable_preview(client, providers):
    providers.tutor.error = LearningError("MODEL_OUTPUT_INVALID", "tutor", "测试失败", 502)
    session = activate(client)
    response = client.post(PREFIX + "/explanations/stream", json=explain_body(session))
    events = [json.loads(line) for line in response.text.splitlines()]
    assert events[-1]["type"] == "error"
    assert not any(event["type"] == "result" for event in events)
    assert client.get(f'{PREFIX}/sessions/{session["session_id"]}/history').json() == []


def test_followup_changing_topic_or_scope_searches_again(client, providers):
    session = activate(client)
    first = client.post(PREFIX + "/explanations", json=explain_body(session, question="解释标签和预测")).json()
    second = client.post(PREFIX + "/explanations", json=explain_body(session, question="解释梯度和反向传播",
        continue_from=first["explanation"]["explanation_id"])).json()
    assert second["status"] == "COMPLETE" and len(providers.sources.calls) == 2
    body = explain_body(session, question="继续解释", continue_from=second["explanation"]["explanation_id"],
        scope={"source_mode": "specified_public", "network_authorized": True,
               "repository_allowlist": ["fixture/repo-b"]})
    assert client.post(PREFIX + "/explanations", json=body).status_code == 200
    assert providers.sources.calls[-1].repository_allowlist == ["fixture/repo-b"]


@pytest.mark.parametrize("url", ["https://external.invalid/v1", "http://127.0.0.1.evil.invalid",
                                 "http://u:p@localhost:1234/v1", "http://localhost:1234/admin"])
def test_picker_cannot_expand_to_remote_or_arbitrary_local_paths(url):
    catalog = TutorCatalog(object())
    with pytest.raises(LearningError, match="INVALID_MODEL_ENDPOINT"):
        catalog.configuration(url)


def test_concurrent_model_selection_does_not_mutate_the_default(monkeypatch):
    from concept_to_code_learning.tutor import catalog as module
    def factory(config):
        return AsyncLocalModelAdapter(config, transport=httpx.MockTransport(
            lambda request: httpx.Response(200, json={"data": [{"id": "small"}, {"id": "large"}]})))
    monkeypatch.setattr(module, "AsyncLocalModelAdapter", factory)
    async def scenario():
        config = LocalModelConfig("http://127.0.0.1:12345/v1", "small")
        default = GroundedTutorProvider(factory(config), config)
        catalog = TutorCatalog(default)
        small, large = await asyncio.gather(catalog.resolve("small"), catalog.resolve("large"))
        assert small is default and large is not default
        assert default.config.model == "small" and large.config.model == "large"
        with pytest.raises(LearningError, match="MODEL_NOT_FOUND"):
            await catalog.resolve("not-served")
        await catalog.close()
        await default.close()
    asyncio.run(scenario())


@pytest.mark.parametrize("finish,model,valid", [("stop", "test", True), (None, "test", False),
                                              ("length", "test", False), ("stop", "other", False)])
def test_model_stream_preserves_usage_and_rejects_partial_or_wrong_identity(finish, model, valid):
    async def scenario():
        events = [{"model": model, "choices": [{"index": 0, "delta": {"content": '{"text":"中文"}'},
                                                  "finish_reason": finish}]},
                  {"model": model, "choices": [], "usage": {"prompt_tokens": 12, "completion_tokens": 8}}]
        payload = "".join("data: " + json.dumps(item) + "\n\n" for item in events) + "data: [DONE]\n\n"
        adapter = AsyncLocalModelAdapter(LocalModelConfig("http://127.0.0.1:12345", "test"),
            transport=httpx.MockTransport(lambda request: httpx.Response(200,
                headers={"content-type": "text/event-stream"}, content=payload)))
        previews = []
        result = await adapter.generate([{"role": "user", "content": "question"}], on_text=previews.append)
        assert result.ok is valid
        if valid:
            assert result.text == '{"text":"中文"}' and previews[-1] == result.text
            assert result.usage["provider_usage"] == {"prompt_tokens": 12, "completion_tokens": 8}
        await adapter.close()
    asyncio.run(scenario())


def test_partial_prose_does_not_preview_citation_metadata_or_treat_it_as_complete():
    raw = '{"answer_sections":[{"title":"说明","text":"第一段"},{"title":"源码","text":"第二'
    assert preview_sections(raw) == [{"title": "说明", "text": "第一段"}, {"title": "源码", "text": "第二"}]
    assert preview_sections('{"concept_code_links":[{"text":"not prose"}]}') == []
    assert preview_sections('{"answer_sections":[{"text":"escaped \\\"quote\\\"') == [
        {"title": "", "text": 'escaped "quote"'}]


def test_prediction_guides_and_examples_include_fit_and_predict_not_just_a_docstring():
    guide = guide_for("解释 Label Y (target) 与输入 X 的关系")
    assert guide_for_terms(guide.terms) is guide
    assert "scikit-learn/scikit-learn" in guide.repositories
    text = '"""prediction' + '\nheader' * 90 + '\n"""\nX, y = load()\nmodel.fit(X, y)\nmodel.predict(X)'
    _, start, end, code = excerpt(text, "example.py", None, guide.terms)
    assert start > 70 and end > 90 and "model.fit(X, y)" in code and "model.predict(X)" in code


def test_known_concept_planning_does_not_spend_a_generation(client):
    async def scenario():
        context = m.DocumentContext.model_validate(activate(client)["context"])
        class NoGeneration:
            async def generate(self, *args, **kwargs):
                raise AssertionError("Known retrieval hints do not require a model call")
        tutor = GroundedTutorProvider(NoGeneration())
        plan = await tutor.plan(context, "解释输入 X、标签 Y 与预测", "Source-code", [])
        assert "predict" in plan.source_query.concept_terms and plan.needs_code
        # An explicit new question outranks the old selected text and guide order.
        context = context.model_copy(update={"selected_text": "Label Y is the target to predict"})
        plan = await tutor.plan(context, "现在结合代码解释聚类", "Source-code", [])
        assert "kmeans" in plan.source_query.concept_terms
        # A generic continuation keeps the most recent topic, not the older quote.
        plan = await tutor.plan(context, "继续解释里面的实现", "Source-code", [plan])
        assert "kmeans" in plan.source_query.concept_terms
    asyncio.run(scenario())
