"""Durable annotation storage, separate from original documents and legacy notebooks."""

import sqlite3
from contextlib import closing, contextmanager
from pathlib import Path

from concept_to_code_learning.full_contracts.annotations import Annotation, AnnotationAnchor
from concept_to_code_learning.full_contracts.models import DocumentContext, digest, utcnow
from concept_to_code_learning.full_learning.errors import LearningError, require
from concept_to_code_learning.full_learning.store import canonical


class AnnotationStore:
    def __init__(self, folder: Path):
        self.path = folder / "annotations-v1.sqlite3"
        with self.transaction() as db:
            db.execute("CREATE TABLE IF NOT EXISTS annotations(id TEXT PRIMARY KEY, document_id TEXT "
                       "NOT NULL, unit_id TEXT NOT NULL, revision INTEGER NOT NULL, body TEXT NOT NULL, "
                       "create_fingerprint TEXT NOT NULL)")
            db.execute("CREATE INDEX IF NOT EXISTS annotations_location ON annotations(document_id,unit_id)")
            db.execute("CREATE TABLE IF NOT EXISTS annotation_tombstones(id TEXT PRIMARY KEY)")

    @contextmanager
    def transaction(self, write=True):
        try:
            with closing(sqlite3.connect(self.path, timeout=10)) as db, db:
                db.row_factory = sqlite3.Row
                if write:
                    db.execute("BEGIN IMMEDIATE")
                yield db
        except sqlite3.Error as exc:
            raise LearningError("STORAGE_FAILURE", "annotations", "批注未保存，请检查本地数据目录后重试。",
                                503, retryable=True) from exc

    @staticmethod
    def get(db, annotation_id):
        row = db.execute("SELECT * FROM annotations WHERE id=?", (annotation_id,)).fetchone()
        require(row is not None, "ANNOTATION_NOT_FOUND", "annotations", "这条批注已不存在，请刷新列表。", 404)
        return row, Annotation.model_validate_json(row["body"])

    def create(self, annotation_id: str, context: DocumentContext, comment: str) -> Annotation:
        require(bool(context.selected_text.strip()) and context.selection_locator is not None,
                "SELECTION_REQUIRED", "annotations", "请先划选需要批注的原文。")
        anchor = AnnotationAnchor.model_validate({key: getattr(context, key)
                                                 for key in AnnotationAnchor.model_fields})
        fingerprint = digest(canonical({"anchor": anchor.model_dump(mode="json"), "comment": comment}))
        with self.transaction() as db:
            require(db.execute("SELECT id FROM annotation_tombstones WHERE id=?", (annotation_id,)).fetchone() is None,
                    "ANNOTATION_DELETED", "annotations", "这条批注已删除，迟到的保存不会恢复它。", 409)
            old = db.execute("SELECT * FROM annotations WHERE id=?", (annotation_id,)).fetchone()
            if old:
                require(old["create_fingerprint"] == fingerprint, "ANNOTATION_CONFLICT", "annotations",
                        "此保存标识已用于另一条批注，请重新选择原文。", 409)
                return Annotation.model_validate_json(old["body"])
            now = utcnow()
            value = Annotation(mode=context.mode, annotation_id=annotation_id, anchor=anchor,
                               comment=comment, created_at=now, updated_at=now)
            db.execute("INSERT INTO annotations VALUES (?,?,?,?,?,?)", (
                annotation_id, anchor.document_id, anchor.unit_id, 1, canonical(value), fingerprint))
        return value

    def list(self, document_id: str, unit_id: str | None, offset: int, limit: int):
        clause, values = "document_id=?", [document_id]
        if unit_id:
            clause += " AND unit_id=?"
            values.append(unit_id)
        with self.transaction(False) as db:
            total = db.execute("SELECT COUNT(*) FROM annotations WHERE " + clause, values).fetchone()[0]
            rows = db.execute("SELECT body FROM annotations WHERE " + clause + " ORDER BY rowid DESC LIMIT ? OFFSET ?",
                              [*values, limit, offset]).fetchall()
        return [Annotation.model_validate_json(row["body"]) for row in rows], total

    def edit(self, annotation_id: str, revision: int, comment: str):
        with self.transaction() as db:
            _, old = self.get(db, annotation_id)
            require(old.revision == revision, "ANNOTATION_REVISION_CONFLICT", "annotations",
                    "批注已在别处更新，请刷新后查看最新内容；当前输入仍保留。", 409)
            value = Annotation.model_validate({**old.model_dump(), "comment": comment,
                                              "revision": old.revision + 1, "updated_at": utcnow()})
            db.execute("UPDATE annotations SET revision=?,body=? WHERE id=?",
                       (value.revision, canonical(value), annotation_id))
        return value

    def delete(self, annotation_id: str, revision: int, confirmed: bool):
        require(confirmed, "DELETE_CONFIRMATION_REQUIRED", "annotations", "删除批注需要明确确认。")
        with self.transaction() as db:
            _, value = self.get(db, annotation_id)
            require(value.revision == revision, "ANNOTATION_REVISION_CONFLICT", "annotations",
                    "批注已更新，请刷新后再删除。", 409)
            db.execute("INSERT INTO annotation_tombstones VALUES (?)", (annotation_id,))
            db.execute("DELETE FROM annotations WHERE id=?", (annotation_id,))
