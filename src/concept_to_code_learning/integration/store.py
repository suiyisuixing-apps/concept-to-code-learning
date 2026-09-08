"""New versioned tables in the existing SQLite store; legacy rows are never rewritten."""

import json
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from uuid import uuid4

from concept_to_code_learning.integration.contracts import require, validate
from concept_to_code_learning.integration.errors import SliceError


class SnapshotNoteStore:
    def __init__(self, legacy_store, schemas: dict):
        self.storage = legacy_store
        self.schemas = schemas
        with closing(self.storage.connect()) as db, db:
            db.execute("CREATE TABLE IF NOT EXISTS sprint_explanations "
                       "(id TEXT PRIMARY KEY, body TEXT NOT NULL)")
            db.execute("CREATE TABLE IF NOT EXISTS sprint_notes "
                       "(id TEXT PRIMARY KEY, body TEXT NOT NULL)")

    def remember(self, explanation: dict) -> None:
        validate("grounded-explanation", explanation, self.schemas)
        try:
            with closing(self.storage.connect()) as db, db:
                db.execute("INSERT INTO sprint_explanations VALUES (?, ?)",
                           (explanation["grounded_explanation_id"], json.dumps(explanation)))
        except sqlite3.Error as exc:
            raise SliceError("EXPLANATION_SAVE_FAILED", "storage",
                             "Explanation could not be stored; no personal note was created", 503
                             ) from exc

    def save(self, explanation_id: str, title: str, user_text: str,
             save_requested_by_user: bool) -> dict:
        require(save_requested_by_user is True, "EXPLICIT_SAVE_REQUIRED", "note",
                "A separate, explicit user save is required")
        require(isinstance(title, str) and 0 < len(title.strip()) <= 160
                and isinstance(user_text, str) and len(user_text) <= 20000,
                "INVALID_NOTE", "note", "Provide a title and bounded personal text")
        try:
            with closing(self.storage.connect()) as db, db:
                row = db.execute("SELECT body FROM sprint_explanations WHERE id = ?",
                                 (explanation_id,)).fetchone()
                if row is None:
                    raise SliceError("EXPLANATION_NOT_FOUND", "note",
                                     "Generate a Sprint 1 explanation before saving", 404)
                snapshot = json.loads(row[0])
                now = datetime.now(timezone.utc).isoformat()
                note = {"contract_version": "sprint-1", "note_id": str(uuid4()),
                        "title": title.strip(), "user_text": user_text,
                        "grounded_explanation_id": explanation_id,
                        "explanation_snapshot": snapshot, "grounded_explanation": snapshot,
                        "document_sources": snapshot["document_citations"],
                        "github_sources": snapshot["github_sources"],
                        "created_at": now, "updated_at": now, "authored_by_user": True,
                        "mode": snapshot["mode"], "status": snapshot["status"]}
                validate("saved-note", note, self.schemas)
                db.execute("INSERT INTO sprint_notes VALUES (?, ?)",
                           (note["note_id"], json.dumps(note)))
            return note
        except sqlite3.Error as exc:
            raise SliceError("NOTE_SAVE_FAILED", "storage",
                             "Note could not be saved; previous notes were not changed", 503) from exc

    def list(self) -> list[dict]:
        try:
            with closing(self.storage.connect()) as db, db:
                rows = db.execute("SELECT body FROM sprint_notes ORDER BY rowid DESC").fetchall()
            return [json.loads(row[0]) for row in rows]
        except sqlite3.Error as exc:
            raise SliceError("NOTE_READ_FAILED", "storage", "Notes could not be read", 503) from exc
