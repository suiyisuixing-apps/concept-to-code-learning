"""Separate additive SQLite storage; never migrates or rewrites legacy notebooks.

Every connection is owned by one lexical transaction. No await occurs while a
transaction is open. BEGIN IMMEDIATE serializes idempotency and revision checks.
"""

import json
import sqlite3
from contextlib import closing, contextmanager
from pathlib import Path

from pydantic import BaseModel

from concept_to_code_learning.full_contracts.models import (
    CodeEvidence,
    DocumentContext,
    EditNoteRequest,
    ExplanationRequest,
    ExplanationResult,
    SavedNote,
    SaveNoteRequest,
    SearchResult,
    SessionRecord,
    SourceQuery,
    digest,
    uid,
    utcnow,
)
from concept_to_code_learning.full_learning.errors import LearningError, require


def canonical(value) -> str:
    if isinstance(value, BaseModel):
        value = value.model_dump(mode="json")
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


class LearningStore:
    def __init__(self, folder: Path):
        try:
            folder.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise LearningError("STORAGE_FAILURE", "storage", "无法创建应用数据目录。", 503) from exc
        self.path = folder / "learning-v1.sqlite3"
        with self.transaction() as db:
            for statement in (
                "CREATE TABLE IF NOT EXISTS fd_sessions(id TEXT PRIMARY KEY, body TEXT NOT NULL)",
                "CREATE TABLE IF NOT EXISTS fd_requests(id TEXT PRIMARY KEY, session_id TEXT "
                "NOT NULL, epoch INTEGER NOT NULL, fingerprint TEXT NOT NULL, state TEXT "
                "NOT NULL, body TEXT)",
                "CREATE TABLE IF NOT EXISTS fd_explanations(id TEXT PRIMARY KEY, session_id "
                "TEXT NOT NULL, epoch INTEGER NOT NULL, body TEXT NOT NULL)",
                "CREATE TABLE IF NOT EXISTS fd_queries(id TEXT PRIMARY KEY, session_id TEXT "
                "NOT NULL, epoch INTEGER NOT NULL, scope_hash TEXT NOT NULL, query TEXT NOT NULL, "
                "result TEXT NOT NULL)",
                "CREATE TABLE IF NOT EXISTS fd_sources(session_id TEXT NOT NULL, id TEXT NOT NULL, "
                "query_id TEXT NOT NULL, body TEXT NOT NULL, body_hash TEXT NOT NULL, "
                "PRIMARY KEY(session_id,id))",
                "CREATE TABLE IF NOT EXISTS fd_notes(id TEXT PRIMARY KEY, revision INTEGER NOT "
                "NULL, snapshot TEXT NOT NULL, snapshot_hash TEXT NOT NULL, created_at TEXT NOT NULL)",
                "CREATE TABLE IF NOT EXISTS fd_note_revisions(note_id TEXT NOT NULL REFERENCES "
                "fd_notes(id) ON DELETE CASCADE, revision INTEGER NOT NULL, title TEXT NOT NULL, "
                "user_text TEXT NOT NULL, updated_at TEXT NOT NULL, PRIMARY KEY(note_id,revision))",
                "CREATE TABLE IF NOT EXISTS fd_save_keys(session_id TEXT NOT NULL, key TEXT NOT "
                "NULL, fingerprint TEXT NOT NULL, note_id TEXT NOT NULL, PRIMARY KEY(session_id,key))",
            ):
                db.execute(statement)

    def connect(self) -> sqlite3.Connection:
        db = sqlite3.connect(self.path, timeout=10)
        try:
            db.row_factory = sqlite3.Row
            db.execute("PRAGMA foreign_keys=ON")
        except BaseException:
            db.close()
            raise
        return db

    @contextmanager
    def transaction(self, *, write: bool = True):
        try:
            with closing(self.connect()) as db, db:
                if write:
                    db.execute("BEGIN IMMEDIATE")
                yield db
        except sqlite3.Error as exc:
            raise LearningError("STORAGE_FAILURE", "storage",
                                "本地数据操作失败；本次事务已回滚。", 503,
                                retryable=True, needed_action="检查可用磁盘空间和数据目录权限。") from exc

    @staticmethod
    def _session(db, session_id: str) -> SessionRecord:
        row = db.execute("SELECT body FROM fd_sessions WHERE id=?", (session_id,)).fetchone()
        require(row is not None, "SESSION_NOT_FOUND", "session", "会话不存在，请创建新会话。", 404)
        return SessionRecord.model_validate_json(row["body"])

    def create_session(self) -> SessionRecord:
        session = SessionRecord(mode="UNAVAILABLE", session_id=uid(), context_revision=0,
                                status="EMPTY", created_at=utcnow())
        with self.transaction() as db:
            db.execute("INSERT INTO fd_sessions VALUES (?,?)", (session.session_id, canonical(session)))
        return session

    def session(self, session_id: str) -> SessionRecord:
        with self.transaction(write=False) as db:
            return self._session(db, session_id)

    def activate(self, session_id: str, context: DocumentContext, expected_revision: int) -> SessionRecord:
        with self.transaction() as db:
            old = self._session(db, session_id)
            require(old.context_revision == expected_revision, "CONTEXT_REVISION_CONFLICT", "context",
                    "已有更新的导航结果；请刷新会话版本后重试最新操作。", 409)
            session = SessionRecord(mode=context.mode, session_id=session_id,
                                    revision=old.revision + 1,
                                    context_revision=old.context_revision + 1, context=context,
                                    status="READY", created_at=old.created_at)
            db.execute("UPDATE fd_sessions SET body=? WHERE id=?", (canonical(session), session_id))
            db.execute("UPDATE fd_requests SET state='CANCELLED' WHERE session_id=? "
                       "AND state='RUNNING'", (session_id,))
        return session

    @staticmethod
    def _current(db, session_id: str, epoch: int) -> SessionRecord:
        session = LearningStore._session(db, session_id)
        require(session.context is not None and session.context_revision == epoch,
                "CANCELLED", "context", "页面或选区已变化，请基于当前位置重新提问。", 409)
        return session

    def begin(self, request: ExplanationRequest) -> ExplanationResult | None:
        fingerprint = digest(canonical(request))
        with self.transaction() as db:
            self._current(db, request.session_id, request.context_revision)
            row = db.execute("SELECT * FROM fd_requests WHERE id=?", (request.request_id,)).fetchone()
            if row:
                require(row["session_id"] == request.session_id and row["fingerprint"] == fingerprint,
                        "REQUEST_CONFLICT", "request", "请求 ID 已用于不同内容。", 409)
                if row["state"] == "COMPLETE":
                    return ExplanationResult.model_validate_json(row["body"])
                raise LearningError("REQUEST_CONFLICT", "request", "请求已执行或正在执行，请使用新 ID。", 409)
            db.execute("INSERT INTO fd_requests VALUES (?,?,?,?,?,NULL)",
                       (request.request_id, request.session_id, request.context_revision,
                        fingerprint, "RUNNING"))
        return None

    def check_request(self, request_id: str):
        with self.transaction(write=False) as db:
            row = db.execute("SELECT * FROM fd_requests WHERE id=?", (request_id,)).fetchone()
            require(row is not None and row["state"] == "RUNNING", "CANCELLED", "request",
                    "请求已取消，迟到结果不会写入当前会话。", 409)
            self._current(db, row["session_id"], row["epoch"])

    def cancel(self, session_id: str, request_id: str) -> None:
        with self.transaction() as db:
            row = db.execute("SELECT state FROM fd_requests WHERE id=? AND session_id=?",
                             (request_id, session_id)).fetchone()
            require(row is not None, "REQUEST_NOT_FOUND", "request", "请求不存在。", 404)
            require(row["state"] != "COMPLETE", "REQUEST_COMPLETE", "request", "请求已经完成。", 409)
            db.execute("UPDATE fd_requests SET state='CANCELLED' WHERE id=?", (request_id,))

    def fail(self, request_id: str, state: str = "FAILED") -> None:
        with self.transaction() as db:
            db.execute("UPDATE fd_requests SET state=? WHERE id=? AND state='RUNNING'",
                       (state, request_id))

    def complete(self, result: ExplanationResult) -> None:
        with self.transaction() as db:
            session = self._current(db, result.session_id, result.context_revision)
            row = db.execute("SELECT state FROM fd_requests WHERE id=?", (result.request_id,)).fetchone()
            require(row is not None and row["state"] == "RUNNING", "CANCELLED", "request",
                    "请求已取消，未保存迟到结果。", 409)
            if result.explanation:
                db.execute("INSERT INTO fd_explanations VALUES (?,?,?,?)",
                           (result.explanation.explanation_id, result.session_id,
                            result.context_revision, canonical(result)))
                session.explanation_ids = (session.explanation_ids + [
                    result.explanation.explanation_id])[-20:]
                db.execute("UPDATE fd_sessions SET body=? WHERE id=?",
                           (canonical(session), result.session_id))
            db.execute("UPDATE fd_requests SET state='COMPLETE',body=? WHERE id=?",
                       (canonical(result), result.request_id))

    def explanation(self, session_id: str, explanation_id: str) -> ExplanationResult:
        with self.transaction(write=False) as db:
            row = db.execute("SELECT body FROM fd_explanations WHERE id=? AND session_id=?",
                             (explanation_id, session_id)).fetchone()
            require(row is not None, "EXPLANATION_NOT_FOUND", "session", "当前会话没有此讲解。", 404)
            return ExplanationResult.model_validate_json(row["body"])

    def put_query(self, session_id: str, epoch: int, query: SourceQuery,
                  scope_hash: str, result: SearchResult) -> None:
        with self.transaction() as db:
            self._current(db, session_id, epoch)
            db.execute("INSERT INTO fd_queries VALUES (?,?,?,?,?,?)",
                       (query.query_id, session_id, epoch, scope_hash, canonical(query), canonical(result)))

    def query(self, session_id: str, query_id: str) -> tuple[SourceQuery, SearchResult, str]:
        with self.transaction(write=False) as db:
            row = db.execute("SELECT * FROM fd_queries WHERE id=? AND session_id=?",
                             (query_id, session_id)).fetchone()
            require(row is not None, "SOURCE_MISMATCH", "sources", "检索不属于当前会话。", 404)
            self._current(db, session_id, row["epoch"])
            return (SourceQuery.model_validate_json(row["query"]),
                    SearchResult.model_validate_json(row["result"]), row["scope_hash"])

    def put_source(self, session_id: str, query_id: str, evidence: CodeEvidence) -> None:
        body = canonical(evidence)
        with self.transaction() as db:
            query = db.execute("SELECT epoch FROM fd_queries WHERE id=? AND session_id=?",
                               (query_id, session_id)).fetchone()
            require(query is not None, "SOURCE_MISMATCH", "sources", "来源缺少检索绑定。", 409)
            self._current(db, session_id, query["epoch"])
            old = db.execute("SELECT body_hash,query_id FROM fd_sources WHERE session_id=? AND id=?",
                             (session_id, evidence.source_id)).fetchone()
            if old:
                require(old["body_hash"] == digest(body) and old["query_id"] == query_id,
                        "SOURCE_MISMATCH", "sources", "来源 ID 已用于不同内容或检索。", 409)
            else:
                db.execute("INSERT INTO fd_sources VALUES (?,?,?,?,?)",
                           (session_id, evidence.source_id, query_id, body, digest(body)))

    def source(self, session_id: str, source_id: str) -> tuple[CodeEvidence, SourceQuery, str]:
        with self.transaction(write=False) as db:
            row = db.execute("SELECT * FROM fd_sources WHERE session_id=? AND id=?",
                             (session_id, source_id)).fetchone()
            require(row is not None, "SOURCE_MISMATCH", "sources", "来源不属于当前会话。", 404)
            require(digest(row["body"]) == row["body_hash"], "SOURCE_MISMATCH", "sources",
                    "缓存来源内容校验失败。", 409)
            evidence = CodeEvidence.model_validate_json(row["body"])
            query_id = row["query_id"]
        query, _, scope_hash = self.query(session_id, query_id)
        return evidence, query, scope_hash

    @staticmethod
    def _note(db, note_id: str, revision: int | None = None) -> SavedNote:
        note = db.execute("SELECT * FROM fd_notes WHERE id=?", (note_id,)).fetchone()
        require(note is not None, "NOTE_NOT_FOUND", "notes", "笔记不存在或已删除。", 404)
        rev = db.execute("SELECT * FROM fd_note_revisions WHERE note_id=? AND revision=?",
                         (note_id, revision or note["revision"])).fetchone()
        require(rev is not None, "NOTE_NOT_FOUND", "notes", "笔记修订不存在。", 404)
        require(digest(note["snapshot"]) == note["snapshot_hash"], "STORAGE_FAILURE", "notes",
                "笔记来源快照校验失败，请从备份恢复。", 503)
        snapshot = json.loads(note["snapshot"])
        return SavedNote(mode=snapshot["explanation"]["mode"], note_id=note_id,
                         revision=rev["revision"], title=rev["title"], user_text=rev["user_text"],
                         explanation_snapshot=snapshot["explanation"],
                         document_snapshot=snapshot["document"],
                         code_evidence_snapshot=snapshot["sources"],
                         snapshot_sha256=note["snapshot_hash"], created_at=note["created_at"],
                         updated_at=rev["updated_at"])

    def save_note(self, request: SaveNoteRequest) -> SavedNote:
        require(request.save_requested_by_user, "EXPLICIT_SAVE_REQUIRED", "notes",
                "只有用户明确保存才能创建个人笔记。")
        require(bool(request.title.strip()), "INVALID_NOTE", "notes", "请填写笔记标题。")
        fingerprint = digest(canonical(request))
        with self.transaction() as db:
            old = db.execute("SELECT * FROM fd_save_keys WHERE session_id=? AND key=?",
                             (request.session_id, request.idempotency_key)).fetchone()
            if old:
                require(old["fingerprint"] == fingerprint, "IDEMPOTENCY_CONFLICT", "notes",
                        "相同保存请求 ID 对应不同内容。", 409)
                # Deletion keeps only the idempotency tombstone, so a late retry cannot resurrect it.
                return self._note(db, old["note_id"], 1)
            row = db.execute("SELECT body FROM fd_explanations WHERE id=? AND session_id=?",
                             (request.explanation_id, request.session_id)).fetchone()
            require(row is not None, "EXPLANATION_NOT_FOUND", "notes", "会话讲解不存在。", 404)
            result = ExplanationResult.model_validate_json(row["body"])
            require(result.explanation is not None, "EXPLANATION_NOT_FOUND", "notes", "讲解未完成。", 409)
            snapshot = canonical({"explanation": result.explanation.model_dump(mode="json"),
                                  "document": result.explanation.context_snapshot.model_dump(mode="json"),
                                  "sources": [item.model_dump(mode="json") for item in (
                                      result.sources + result.source_observations)]})
            note_id, now = uid(), utcnow().isoformat()
            db.execute("INSERT INTO fd_notes VALUES (?,?,?,?,?)",
                       (note_id, 1, snapshot, digest(snapshot), now))
            db.execute("INSERT INTO fd_note_revisions VALUES (?,?,?,?,?)",
                       (note_id, 1, request.title.strip(), request.user_text, now))
            db.execute("INSERT INTO fd_save_keys VALUES (?,?,?,?)",
                       (request.session_id, request.idempotency_key, fingerprint, note_id))
            return self._note(db, note_id)

    def note(self, note_id: str, revision: int | None = None) -> SavedNote:
        with self.transaction(write=False) as db:
            return self._note(db, note_id, revision)

    def list_notes(self, search: str = "", offset: int = 0, limit: int = 50) -> tuple[list[SavedNote], int]:
        require(0 <= offset and 1 <= limit <= 100 and len(search) <= 200,
                "INVALID_NOTE_QUERY", "notes", "笔记列表参数超出范围。")
        clause = (" FROM fd_notes n JOIN fd_note_revisions r ON n.id=r.note_id "
                  "AND n.revision=r.revision WHERE instr(lower(r.title || char(10) || r.user_text), "
                  "lower(?)) > 0")
        with self.transaction(write=False) as db:
            total = db.execute("SELECT count(*)" + clause, (search,)).fetchone()[0]
            rows = db.execute("SELECT n.id" + clause + " ORDER BY r.updated_at DESC,n.id "
                              "LIMIT ? OFFSET ?", (search, limit, offset)).fetchall()
            return [self._note(db, row[0]) for row in rows], total

    def edit_note(self, note_id: str, request: EditNoteRequest) -> SavedNote:
        require(bool(request.title.strip()), "INVALID_NOTE", "notes", "请填写笔记标题。")
        with self.transaction() as db:
            current = self._note(db, note_id)
            require(current.revision == request.expected_revision, "REVISION_CONFLICT", "notes",
                    "笔记已被编辑，请刷新后重试。", 409)
            revision = current.revision + 1
            db.execute("INSERT INTO fd_note_revisions VALUES (?,?,?,?,?)",
                       (note_id, revision, request.title.strip(), request.user_text, utcnow().isoformat()))
            db.execute("UPDATE fd_notes SET revision=? WHERE id=?", (revision, note_id))
            return self._note(db, note_id)

    def delete_note(self, note_id: str, expected_revision: int, confirmed: bool) -> None:
        require(confirmed, "DELETE_CONFIRMATION_REQUIRED", "notes", "删除笔记需要用户确认。")
        with self.transaction() as db:
            note = self._note(db, note_id)
            require(note.revision == expected_revision, "REVISION_CONFLICT", "notes",
                    "笔记已变化，请刷新后确认删除。", 409)
            db.execute("DELETE FROM fd_notes WHERE id=?", (note_id,))
