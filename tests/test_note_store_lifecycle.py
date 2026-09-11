"""Connection ownership and rollback across legacy callers and the raw connection API."""

import json
import sqlite3
from contextlib import closing
from pathlib import Path

import pytest

from concept_to_code_learning.store import NoteStore
from concept_to_code_learning.tutor.fixture import QUESTION, FixtureTutor

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def tutor():
    return FixtureTutor(ROOT)


@pytest.fixture
def connections(monkeypatch):
    original = sqlite3.connect
    opened = []
    fault = {"prefix": None}

    class Connection(sqlite3.Connection):
        def execute(self, sql, *args, **kwargs):
            result = super().execute(sql, *args, **kwargs)
            if fault["prefix"] and sql.startswith(fault["prefix"]):
                # Failure after a write observes rollback, not just error propagation.
                raise sqlite3.OperationalError("injected operation failure")
            return result

    def connect(*args, **kwargs):
        db = original(*args, **kwargs, factory=Connection)
        opened.append(db)
        return db

    monkeypatch.setattr(sqlite3, "connect", connect)
    return opened, fault, original


def assert_closed(opened):
    assert opened
    for db in opened:
        with pytest.raises(sqlite3.ProgrammingError, match="closed"):
            db.execute("SELECT 1")


def test_success_closes_owned_connections_and_preserves_raw_connect_api(tmp_path, tutor,
                                                                      connections):
    opened, _, _ = connections
    store = NoteStore(tmp_path, tutor.schemas)
    answer = tutor.explain(QUESTION, tutor.context(), "Beginner")
    store.remember(answer)
    note = store.save(answer["grounded_explanation_id"], "Title", "My words")
    assert store.list() == [note]
    assert_closed(opened)
    # SnapshotNoteStore's supported consumer needs execute/close plus transaction scope.
    with closing(store.connect()) as db, db:
        assert isinstance(db, sqlite3.Connection)
        assert db.execute("SELECT body FROM notes").fetchone()[0] == json.dumps(note)
    assert_closed(opened)


@pytest.mark.parametrize("operation", ["initialize", "remember", "save", "list"])
def test_sql_failures_close_connections_and_roll_back_writes(tmp_path, tutor, connections,
                                                           operation):
    opened, fault, original = connections
    if operation == "initialize":
        fault["prefix"] = "CREATE TABLE"
        with pytest.raises(sqlite3.OperationalError, match="injected"):
            NoteStore(tmp_path, tutor.schemas)
        assert_closed(opened)
        return
    store = NoteStore(tmp_path, tutor.schemas)
    answer = tutor.explain(QUESTION, tutor.context(), "Beginner")
    if operation != "remember":
        store.remember(answer)
    fault["prefix"] = {"remember": "INSERT INTO explanations", "save": "INSERT INTO notes",
                       "list": "SELECT body FROM notes"}[operation]
    with pytest.raises(sqlite3.OperationalError, match="injected"):
        if operation == "remember":
            store.remember(answer)
        elif operation == "save":
            store.save(answer["grounded_explanation_id"], "Title", "My words")
        else:
            store.list()
    assert_closed(opened)
    with closing(original(store.path)) as db:
        assert db.execute("SELECT COUNT(*) FROM notes").fetchone()[0] == 0
        assert db.execute("SELECT COUNT(*) FROM explanations").fetchone()[0] == (
            0 if operation == "remember" else 1)


def test_missing_explanation_and_validation_errors_preserve_saved_notes(tmp_path, tutor,
                                                                       connections):
    opened, _, original = connections
    store = NoteStore(tmp_path, tutor.schemas)
    answer = tutor.explain(QUESTION, tutor.context(), "Beginner")
    store.remember(answer)
    saved = store.save(answer["grounded_explanation_id"], "Keep", "Personal text")
    with closing(original(store.path)) as db:
        before = db.execute("SELECT id, body FROM notes").fetchall()
    with pytest.raises(KeyError):
        store.save("missing", "New", "Text")
    with pytest.raises(ValueError):
        store.save(answer["grounded_explanation_id"], "", "Text")
    assert store.list() == [saved]
    assert_closed(opened)
    with closing(original(store.path)) as db:
        assert db.execute("SELECT id, body FROM notes").fetchall() == before
