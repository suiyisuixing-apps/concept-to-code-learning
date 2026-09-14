import asyncio
import threading

import pytest

from concept_to_code_learning.full_contracts import models as m
from concept_to_code_learning.full_learning.errors import LearningError
from concept_to_code_learning.full_learning.io import CommitGate
from concept_to_code_learning.full_learning.service import LearningService
from concept_to_code_learning.full_learning.store import LearningStore

from .conftest import activate, explain_body

PREFIX = "/api/learning/v1"


def test_verified_but_uncertain_source_is_not_used_as_teaching_evidence(client, providers):
    providers.sources.mutate = lambda source: source.model_copy(update={
        "relevance": source.relevance.model_copy(update={"status": "UNCERTAIN", "basis": []})})
    response = client.post(PREFIX + "/explanations", json=explain_body(activate(client)))
    assert response.status_code == 200
    value = response.json()
    assert value["sources"] == [] and value["explanation"]["code_source_ids"] == []
    assert value["source_observations"][0]["relevance"]["status"] == "UNCERTAIN"
    assert "NO_VERIFIED_CODE" in value["warnings"]


def test_corrupt_history_preserves_bytes_and_healthy_followups(client, app):
    session = activate(client)
    first = client.post(PREFIX + "/explanations", json=explain_body(session)).json()
    second = client.post(PREFIX + "/explanations", json=explain_body(session, question="另一个问题")).json()
    store = app.state.learning_service.store
    bad_id = first["explanation"]["explanation_id"]
    with store.transaction() as db:
        db.execute("UPDATE fd_explanations SET body=? WHERE id=?", ('{"broken":"retained"}', bad_id))
    history = client.get(f'{PREFIX}/sessions/{session["session_id"]}/history')
    assert history.status_code == 200 and history.headers["X-C2C-Skipped-History"] == "1"
    assert [x["explanation"]["explanation_id"] for x in history.json()] == [second["explanation"]["explanation_id"]]
    follow = client.post(PREFIX + "/explanations", json=explain_body(session,
        question="继续解释", continue_from=second["explanation"]["explanation_id"]))
    assert follow.status_code == 200 and "HISTORY_PARTIAL" in follow.json()["warnings"]
    new = client.post(PREFIX + "/explanations", json=explain_body(session, question="新问题"))
    assert new.status_code == 200 and "HISTORY_PARTIAL" in new.json()["warnings"]
    with store.transaction(write=False) as db:
        assert db.execute("SELECT body FROM fd_explanations WHERE id=?", (bad_id,)).fetchone()[0] == '{"broken":"retained"}'


def test_broken_recent_session_does_not_hide_healthy_session(client, app):
    session = activate(client)
    with app.state.learning_service.store.transaction() as db:
        db.execute("INSERT INTO fd_sessions VALUES (?,?)", ("broken-session", "not-json"))
    assert client.get(PREFIX + "/sessions/recent").json()["session_id"] == session["session_id"]


def test_unexpected_storage_and_provider_errors_are_structured_and_private(client, app, providers, monkeypatch, caplog):
    def broken():
        raise RuntimeError("/private/path sk-SECRET-PROBE question contents")

    monkeypatch.setattr(app.state.learning_service.store, "create_session", broken)
    response = client.post(PREFIX + "/sessions")
    assert response.status_code == 500 and response.json()["code"] == "INTERNAL_ERROR"
    assert not response.json()["retryable"]
    assert "RuntimeError" in caplog.text and "test_review_regressions.py" in caplog.text
    assert "sk-SECRET" not in caplog.text + response.text
    assert "/private/path" not in caplog.text + response.text

    async def provider_bug(*args):
        raise AttributeError("private provider response")

    providers.document.get_unit = provider_bug
    response = client.get(PREFIX + "/documents/doc-PDF/units/unit-PDF")
    assert response.status_code == 500 and response.json()["code"] == "INTERNAL_ERROR"
    assert "private provider response" not in caplog.text + response.text


def test_cancel_during_slow_begin_finishes_transaction_before_cleanup(tmp_path, providers, monkeypatch):
    async def scenario():
        store = LearningStore(tmp_path)
        service = LearningService(providers, store)
        session = store.create_session()
        session = await service.activate(session.session_id, m.ActivateContext(document_id="doc-PDF",
            document_revision=1, unit_id="unit-PDF", expected_context_revision=0))
        request = m.ExplanationRequest.model_validate(explain_body(session.model_dump(mode="json")))
        entered, release = threading.Event(), threading.Event()
        original = store.begin

        def slow_begin(body):
            entered.set()
            assert release.wait(3)
            return original(body)

        monkeypatch.setattr(store, "begin", slow_begin)
        task = asyncio.create_task(service.explain(request))
        try:
            assert await asyncio.to_thread(entered.wait, 2)
            task.cancel()
            await asyncio.sleep(0)
            assert not task.done()
        finally:
            release.set()
        with pytest.raises(LearningError, match="CANCELLED"):
            await task
        with store.transaction(write=False) as db:
            assert db.execute("SELECT state FROM fd_requests WHERE id=?", (request.request_id,)).fetchone()[0] == "CANCELLED"
            assert db.execute("SELECT count(*) FROM fd_explanations").fetchone()[0] == 0
        assert not service.active
        await service.close()
    asyncio.run(scenario())


def test_duplicate_running_request_does_not_fail_its_owner(tmp_path, providers):
    async def scenario():
        store = LearningStore(tmp_path)
        service = LearningService(providers, store)
        session = store.create_session()
        session = await service.activate(session.session_id, m.ActivateContext(document_id="doc-PDF",
            document_revision=1, unit_id="unit-PDF", expected_context_revision=0))
        request = m.ExplanationRequest.model_validate(explain_body(session.model_dump(mode="json")))
        providers.tutor.delay = True
        first = asyncio.create_task(service.explain(request))
        await asyncio.wait_for(providers.tutor.started.wait(), 2)
        with pytest.raises(LearningError):
            await service.explain(request)
        store.check_request(request.request_id)
        assert service.active[request.request_id] is first
        providers.tutor.release.set()
        assert (await first).status == "COMPLETE"
        await service.close()
    asyncio.run(scenario())


@pytest.mark.parametrize("commit_wins", [False, True])
def test_cancellation_at_commit_boundary_reports_actual_database_outcome(tmp_path, providers, monkeypatch, commit_wins):
    async def scenario():
        store = LearningStore(tmp_path)
        service = LearningService(providers, store)
        session = store.create_session()
        session = await service.activate(session.session_id, m.ActivateContext(document_id="doc-PDF",
            document_revision=1, unit_id="unit-PDF", expected_context_revision=0))
        request = m.ExplanationRequest.model_validate(explain_body(session.model_dump(mode="json")))
        entered, release = threading.Event(), threading.Event()
        original = CommitGate.start

        def held_commit(gate):
            if commit_wins:
                original(gate)
            entered.set()
            assert release.wait(3)
            if not commit_wins:
                original(gate)

        monkeypatch.setattr(CommitGate, "start", held_commit)
        task = asyncio.create_task(service.explain(request))
        try:
            assert await asyncio.to_thread(entered.wait, 2)
            task.cancel()
            await asyncio.sleep(0)
        finally:
            release.set()
        if commit_wins:
            assert (await task).status == "COMPLETE"
        else:
            with pytest.raises(LearningError, match="CANCELLED"):
                await task
        with store.transaction(write=False) as db:
            assert db.execute("SELECT state FROM fd_requests WHERE id=?", (request.request_id,)).fetchone()[0] == ("COMPLETE" if commit_wins else "CANCELLED")
            assert db.execute("SELECT count(*) FROM fd_explanations").fetchone()[0] == int(commit_wins)
        assert not service.active and not service.request_sessions
        await service.close()
    asyncio.run(scenario())


def test_disconnected_stream_with_full_progress_queue_cannot_hang_cleanup(app, monkeypatch):
    from concept_to_code_learning.full_learning.api import create_router

    async def scenario():
        async def busy(body, progress):
            for _ in range(20):
                progress("answering")
            try:
                await asyncio.Event().wait()
            except asyncio.CancelledError:
                raise LearningError("CANCELLED", "request", "已取消", 409) from None

        monkeypatch.setattr(app.state.learning_service, "explain", busy)
        router = create_router(app.state.learning_service, None, None)
        route = next(r for r in router.routes if getattr(r, "path", None) == PREFIX + "/explanations/stream")
        response = await route.endpoint(None)
        assert "progress" in await anext(response.body_iterator)
        await asyncio.wait_for(response.body_iterator.aclose(), 1)
    asyncio.run(scenario())
