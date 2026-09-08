"""Local append-only notes. Explanations and citations are snapshotted server-side."""

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from concept_to_code_learning.contracts import validate_record


class NoteStore:
    def __init__(self, folder: Path, schemas: dict):
        folder.mkdir(parents=True, exist_ok=True)
        self.path = folder / "fixture-notes.sqlite3"
        self.schemas = schemas
        with self.connect() as db:
            db.execute("CREATE TABLE IF NOT EXISTS explanations (id TEXT PRIMARY KEY, body TEXT)")
            db.execute("CREATE TABLE IF NOT EXISTS notes (id TEXT PRIMARY KEY, body TEXT)")

    def connect(self):
        return sqlite3.connect(self.path, timeout=10)

    def remember(self, explanation: dict):
        with self.connect() as db:
            db.execute("INSERT INTO explanations VALUES (?, ?)",
                       (explanation["grounded_explanation_id"], json.dumps(explanation)))

    def save(self, explanation_id: str, title: str, user_text: str) -> dict:
        with self.connect() as db:
            row = db.execute("SELECT body FROM explanations WHERE id = ?",
                             (explanation_id,)).fetchone()
            if row is None:
                raise KeyError("Explanation not found; request an explanation before saving")
            explanation = json.loads(row[0])
            now = datetime.now(timezone.utc).isoformat()
            note = {
                "note_id": str(uuid4()), "title": title, "user_text": user_text,
                "grounded_explanation_id": explanation_id,
                "document_sources": explanation["document_citations"],
                "github_sources": explanation["github_sources"],
                "created_at": now, "updated_at": now, "authored_by_user": True,
                "grounded_explanation": explanation, "mode": "FIXTURE",
                "status": "SCAFFOLD_DEMO",
            }
            validate_record("saved-note", note, self.schemas)
            db.execute("INSERT INTO notes VALUES (?, ?)", (note["note_id"], json.dumps(note)))
        return note

    def list(self) -> list[dict]:
        with self.connect() as db:
            rows = db.execute("SELECT body FROM notes ORDER BY rowid DESC").fetchall()
        return [json.loads(row[0]) for row in rows]
