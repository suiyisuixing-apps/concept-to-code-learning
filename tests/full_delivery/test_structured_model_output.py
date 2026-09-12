"""Opt-in endpoint transport contracts; all model responses are synthetic."""

import asyncio
import json

import httpx
import pytest

from concept_to_code_learning.full_learning.providers import ProviderSettings
from concept_to_code_learning.tutor.full import PlanOutput, TeachingOutput, build_provider


@pytest.mark.parametrize("structured", [False, True])
def test_structured_output_is_opt_in_and_thinking_override_is_planning_only(
    structured, monkeypatch, tmp_path
):
    monkeypatch.setenv("C2C_MODEL_BASE_URL", "http://127.0.0.1:12345/v1")
    monkeypatch.setenv("C2C_MODEL_ID", "Qwen-test")
    monkeypatch.setenv("C2C_LOCAL_ROOTS_JSON", "[]")
    monkeypatch.delenv("C2C_MODEL_STRUCTURED_OUTPUT", raising=False)
    if structured:
        monkeypatch.setenv("C2C_MODEL_STRUCTURED_OUTPUT", "1")
    settings = ProviderSettings.from_env(tmp_path, tmp_path / "data")
    assert settings.model_structured_output is structured

    async def scenario():
        tutor = build_provider(settings)
        assert tutor.config.structured_output is structured
        assert tutor.config.timeout_seconds == 60
        assert tutor.config.max_output_tokens == 2500
        calls, previews = [], []
        plan = {"concepts": ["梯度"], "query_terms": ["gradient"], "needs_code": False}
        answer = {"answer": "合成讲解。", "limitations": []}
        reasoning = "synthetic-private-reasoning-not-visible"

        def handler(request):
            body = json.loads(request.content)
            calls.append(body)
            if len(calls) == 1:
                return httpx.Response(200, json={"model": "Qwen-test", "choices": [{
                    "message": {"content": json.dumps(plan), "reasoning_content": reasoning},
                    "finish_reason": "stop"}]})
            content = json.dumps(answer, ensure_ascii=False)
            events = [
                {"model": "Qwen-test", "choices": [{"index": 0,
                    "delta": {"reasoning_content": reasoning}, "finish_reason": None}]},
                {"model": "Qwen-test", "choices": [{"index": 0,
                    "delta": {"content": content[:12]}, "finish_reason": None}]},
                {"model": "Qwen-test", "choices": [{"index": 0,
                    "delta": {"content": content[12:]}, "finish_reason": "stop"}]},
            ]
            stream = "".join("data: " + json.dumps(event) + "\n\n" for event in events)
            return httpx.Response(200, headers={"content-type": "text/event-stream"},
                                  content=stream + "data: [DONE]\n\n")

        tutor.adapter._transport = httpx.MockTransport(handler)
        try:
            planned, plan_result = await tutor._json("plan", {}, PlanOutput)
            taught, teaching_result = await tutor._json(
                "teach", {}, TeachingOutput, on_text=previews.append
            )
        finally:
            await tutor.close()
        assert planned.concepts == ["梯度"] and taught.answer == answer["answer"]
        assert len(previews) == 2 and json.loads(previews[-1]) == answer
        assert reasoning not in plan_result.text + teaching_result.text + "".join(previews)
        for index, call in enumerate(calls):
            expected = {
                "model": "Qwen-test", "messages": call["messages"], "temperature": 0,
                "max_tokens": 550 if index == 0 else 1600, "stream": index == 1,
                "stop": ["<|im_end|>"],
            }
            if index == 1:
                expected["stream_options"] = {"include_usage": True}
            if structured:
                expected["response_format"] = {
                    "type": "json_schema",
                    "json_schema": {"name": "c2c_object", "schema": {"type": "object"}},
                }
                if index == 0:
                    expected["chat_template_kwargs"] = {"enable_thinking": False}
            assert call == expected

    asyncio.run(scenario())
