"""Additive learning API. Browser inputs contain IDs, never verification receipts."""

import asyncio
import hashlib
import json
from urllib.parse import urlsplit

from fastapi import APIRouter, FastAPI, Query, Request
from fastapi.exceptions import RequestValidationError, ResponseValidationError
from fastapi.responses import JSONResponse, Response, StreamingResponse
from pydantic import ValidationError

from concept_to_code_learning.full_contracts import annotations as a
from concept_to_code_learning.full_contracts import models as m
from concept_to_code_learning.full_learning.annotations import AnnotationStore
from concept_to_code_learning.full_learning.errors import LearningError, require
from concept_to_code_learning.full_learning.export import export_note
from concept_to_code_learning.full_learning.ports import DocumentUpload
from concept_to_code_learning.repositories.api import repository_router
from concept_to_code_learning.tutor.catalog import ModelEndpoint, ModelList

PREFIX = "/api/learning/v1"
ERROR_RESPONSES = {status: {"model": m.LearningErrorResponse} for status in (400, 403, 404, 409, 413, 422, 502, 503, 504)}


def create_router(service, legacy_store, sprint_store) -> APIRouter:
    router = APIRouter(prefix=PREFIX, tags=["Full delivery v1"], responses=ERROR_RESPONSES)
    annotations = AnnotationStore(service.store.path.parent)
    if service.repositories:
        router.include_router(repository_router(service.repositories))

    @router.get("/capabilities", response_model=m.Capabilities)
    async def capabilities():
        return await service.capabilities()

    @router.get("/models", response_model=ModelList)
    async def models():
        return await service.models.discover()

    @router.post("/models/discover", response_model=ModelList)
    async def discover_models(body: ModelEndpoint):
        return await service.models.discover(body.base_url)

    @router.post("/sessions", response_model=m.SessionRecord, status_code=201)
    async def session_create():
        return service.store.create_session()

    @router.get("/sessions/recent", response_model=m.SessionRecord | None)
    async def session_recent():
        return service.store.recent_session()

    @router.get("/sessions/{session_id}/history", response_model=list[m.ExplanationResult])
    async def session_history(session_id: m.ID):
        return service.store.history(session_id)

    @router.get("/sessions/{session_id}", response_model=m.SessionRecord)
    async def session_get(session_id: m.ID):
        return service.store.session(session_id)

    @router.post("/sessions/{session_id}/context", response_model=m.SessionRecord)
    async def session_context(session_id: m.ID, body: m.ActivateContext):
        return await service.activate(session_id, body)

    @router.post("/documents", response_model=m.DocumentRecord, status_code=201,
                 openapi_extra={"requestBody": {"required": True, "content": {
                     "application/octet-stream": {"schema": {"type": "string", "format": "binary"}}}}})
    async def upload(request: Request, file_name: str = Query(min_length=1, max_length=240)):
        require(not any(x in file_name for x in ("/", "\\", "\x00")) and file_name not in {".", ".."},
                "INVALID_FILE", "document", "请提供文件显示名，不能提交主机路径。")
        chunks, size = [], 0
        async for chunk in request.stream():
            size += len(chunk)
            require(size <= 20 * 1024 * 1024, "FILE_TOO_LARGE", "document", "文件超过 20 MiB 导入上限。", 413)
            chunks.append(chunk)
        require(size > 0, "INVALID_FILE", "document", "上传文件为空。")
        content = b"".join(chunks)
        record = m.DocumentRecord.model_validate(await service.call(
            "document", service.providers.document.import_document, DocumentUpload(file_name, content)))
        require(record.original_sha256 == hashlib.sha256(content).hexdigest()
                and record.file_name == file_name, "DOCUMENT_VERSION_MISMATCH", "document",
                "导入结果没有绑定所上传的原始文件。", 502)
        return record

    @router.get("/documents", response_model=m.DocumentList)
    async def documents():
        items = await service.call("document", service.providers.document.list_documents)
        capability = await service.provider_capability(service.providers.document, "document")
        return m.DocumentList(mode=capability.mode, documents=items)

    @router.get("/documents/{document_id}", response_model=m.DocumentRecord)
    async def document_record(document_id: m.ID):
        return await service.document_record(document_id)

    @router.get("/documents/{document_id}/units", response_model=m.UnitList)
    async def units(document_id: m.ID):
        items = await service.document_units(document_id)
        capability = await service.provider_capability(service.providers.document, "document")
        return m.UnitList(mode="LIVE" if document_id.startswith("code-") else capability.mode, document_id=document_id, units=items)

    @router.get("/documents/{document_id}/units/{unit_id}", response_model=m.DocumentUnit)
    async def unit(document_id: m.ID, unit_id: m.ID):
        return await service.document_unit(document_id, unit_id)

    @router.post("/documents/{document_id}/context", response_model=m.DocumentContext)
    async def context(document_id: m.ID, body: m.ContextRequest):
        return await service.context(document_id, body)

    @router.get("/documents/{document_id}/assets/{asset_id}")
    async def asset(document_id: m.ID, asset_id: m.ID):
        item = await service.call("document", service.providers.document.get_asset, document_id, asset_id)
        require(item.media_type in {"application/pdf", "image/png", "image/jpeg", "image/webp"},
                "UNSUPPORTED_FORMAT", "document", "预览资产类型未获允许。")
        return Response(item.content, media_type=item.media_type,
                        headers={"X-Content-Type-Options": "nosniff", "Content-Security-Policy": "sandbox"})

    @router.get("/sources/local-handles", response_model=list[m.ID])
    async def local_handles():
        return await service.call("sources", service.providers.sources.local_handles)

    @router.post("/documents/{document_id}/annotations", response_model=a.Annotation, status_code=201)
    async def annotation_create(document_id: m.ID, body: a.CreateAnnotationRequest):
        request = m.ContextRequest.model_validate(body.model_dump(exclude={"annotation_id", "comment"}))
        context = await service.context(document_id, request)
        return annotations.create(body.annotation_id, context, body.comment)

    @router.get("/documents/{document_id}/annotations", response_model=a.AnnotationList)
    async def annotation_list(document_id: m.ID, unit_id: m.ID | None = None,
                              offset: int = Query(default=0, ge=0), limit: int = Query(default=50, ge=1, le=100)):
        items, total = annotations.list(document_id, unit_id, offset, limit)
        mode = "FIXTURE" if any(item.mode == "FIXTURE" for item in items) else ("LIVE" if items else "UNAVAILABLE")
        return a.AnnotationList(mode=mode, document_id=document_id, annotations=items, total=total, offset=offset)

    @router.patch("/annotations/{annotation_id}", response_model=a.Annotation)
    async def annotation_edit(annotation_id: m.ID, body: a.EditAnnotationRequest):
        return annotations.edit(annotation_id, body.expected_revision, body.comment)

    @router.delete("/annotations/{annotation_id}", status_code=204)
    async def annotation_delete(annotation_id: m.ID, body: m.DeleteNoteRequest):
        annotations.delete(annotation_id, body.expected_revision, body.confirmed_by_user)
        return Response(status_code=204)

    @router.post("/sources/search", response_model=m.SearchResult)
    async def search(body: m.SearchRequest):
        return await service.search(body)

    @router.post("/sources/verify", response_model=m.CodeEvidence)
    async def verify(body: m.VerifyRequest):
        return await service.verify(body)

    @router.get("/sources/{source_id}", response_model=m.CodeEvidence)
    async def source(source_id: m.ID, session_id: m.ID):
        return service.store.source(session_id, source_id)[0]

    @router.post("/explanations", response_model=m.ExplanationResult)
    async def explain(body: m.ExplanationRequest, request: Request):
        request.state.learning_request_id = body.request_id
        return await service.explain(body)

    @router.post("/explanations/stream", response_class=StreamingResponse)
    async def stream_explanation(body: m.ExplanationRequest):
        async def events():
            queue = asyncio.Queue(maxsize=16)

            def progress(stage):
                if not queue.full():
                    queue.put_nowait(stage if isinstance(stage, dict) else {"type": "progress", "stage": stage})

            async def run():
                try:
                    result = await service.explain(body, progress=progress)
                    await queue.put({"type": "result", "value": result.model_dump(mode="json")})
                except LearningError as exc:
                    await queue.put({"type": "error", "value": exc.payload(body.request_id)})
                except asyncio.CancelledError:
                    raise
                except Exception:
                    await queue.put({"type": "error", "value": LearningError(
                        "REQUEST_FAILED", "request", "这次回答未能完成，请重试。", 500,
                        retryable=True).payload(body.request_id)})

            task = asyncio.create_task(run())
            try:
                while True:
                    event = await queue.get()
                    yield json.dumps(event, ensure_ascii=False, separators=(",", ":")) + "\n"
                    if event["type"] in {"result", "error"}:
                        break
            finally:
                if not task.done():
                    task.cancel()
                await asyncio.gather(task, return_exceptions=True)
        return StreamingResponse(events(), media_type="application/x-ndjson",
                                 headers={"X-Accel-Buffering": "no"})

    @router.delete("/requests/{request_id}", status_code=204)
    async def cancel(request_id: m.ID, session_id: m.ID):
        await service.cancel(session_id, request_id)
        return Response(status_code=204)

    @router.get("/notes/legacy")
    async def legacy():
        # Return original snapshots with their original version, never a new trust label.
        return {"contract_version": "full-delivery-v1", "read_only": True,
                "phase_0_5": legacy_store.list(), "sprint_1": sprint_store.list()}

    @router.post("/notes", response_model=m.SavedNote, status_code=201)
    async def save(body: m.SaveNoteRequest):
        return service.store.save_note(body)

    @router.get("/notes", response_model=m.NoteList)
    async def notes(q: str = Query(default="", max_length=200), offset: int = Query(default=0, ge=0),
                    limit: int = Query(default=50, ge=1, le=100)):
        items, total = service.store.list_notes(q, offset, limit)
        mode = "FIXTURE" if any(item.mode == "FIXTURE" for item in items) else (
            "LIVE" if items else "UNAVAILABLE")
        return m.NoteList(mode=mode, notes=items, total=total, offset=offset)

    @router.get("/notes/{note_id}", response_model=m.SavedNote)
    async def note(note_id: m.ID, revision: int | None = Query(default=None, ge=1)):
        return service.store.note(note_id, revision)

    @router.patch("/notes/{note_id}", response_model=m.SavedNote)
    async def edit(note_id: m.ID, body: m.EditNoteRequest):
        return service.store.edit_note(note_id, body)

    @router.delete("/notes/{note_id}", status_code=204)
    async def delete(note_id: m.ID, body: m.DeleteNoteRequest):
        service.store.delete_note(note_id, body.expected_revision, body.confirmed_by_user)
        return Response(status_code=204)

    @router.get("/notes/{note_id}/export")
    async def export(note_id: m.ID, format: str = Query(default="markdown", pattern="^(markdown|json)$"),
                     revision: int | None = Query(default=None, ge=1)):
        text, media_type = export_note(service.store.note(note_id, revision), format)
        suffix = "md" if format == "markdown" else "json"
        return Response(text, media_type=media_type,
                        headers={"Content-Disposition": f'attachment; filename="note-{note_id}.{suffix}"',
                                 "X-Content-Type-Options": "nosniff"})

    return router


def install_error_handlers(app: FastAPI, *, dev_origin: str | None = None):
    if dev_origin:
        parsed = urlsplit(dev_origin)
        require(parsed.scheme == "http" and parsed.hostname in {"127.0.0.1", "localhost", "::1"}
                and parsed.path in {"", "/"} and not parsed.username and not parsed.query,
                "INVALID_CONFIGURATION", "configuration", "开发 Origin 必须是明确的本机地址。")

    @app.exception_handler(LearningError)
    async def error(request: Request, exc: LearningError):
        return JSONResponse(exc.payload(getattr(request.state, "learning_request_id", None)),
                            status_code=exc.http_status)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError):
        if request.url.path.startswith(PREFIX):
            return JSONResponse(LearningError("INVALID_REQUEST", "request",
                                "请求字段或数据类型不符合接口，请参考 OpenAPI。").payload(), status_code=422)
        from fastapi.exception_handlers import request_validation_exception_handler
        return await request_validation_exception_handler(request, exc)

    @app.exception_handler(ValidationError)
    @app.exception_handler(ResponseValidationError)
    async def output_error(request: Request, exc: ValidationError | ResponseValidationError):
        return JSONResponse(LearningError("INVALID_PROVIDER_RESPONSE", "provider",
                            "模块返回的内容不符合协议，未将其当作成功结果。", 502).payload(), status_code=502)

    @app.middleware("http")
    async def local_request_boundary(request: Request, call_next):
        if request.url.path.startswith(PREFIX) and request.method not in {"GET", "HEAD", "OPTIONS"}:
            origin = request.headers.get("origin")
            allowed = {str(request.base_url).rstrip("/")}
            if dev_origin:
                allowed.add(dev_origin.rstrip("/"))
            if origin and origin not in allowed:
                return JSONResponse(LearningError("ORIGIN_NOT_AUTHORIZED", "request",
                                    "此页面未获准操作本地学习服务。", 403).payload(), status_code=403)
            length = request.headers.get("content-length")
            if length and (not length.isdigit() or int(length) > 21 * 1024 * 1024):
                return JSONResponse(LearningError("FILE_TOO_LARGE", "request",
                                    "请求超过大小上限。", 413).payload(), status_code=413)
        response = await call_next(request)
        if request.url.path.startswith(PREFIX):
            response.headers["Cache-Control"] = "no-store"
            response.headers["X-Content-Type-Options"] = "nosniff"
        return response
