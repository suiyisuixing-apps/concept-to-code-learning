"""Loopback-only fixture API; no runtime outbound network or repository mutation."""

import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field
from starlette.middleware.trustedhost import TrustedHostMiddleware

from concept_to_code_learning import __version__
from concept_to_code_learning.integration.api import create_router
from concept_to_code_learning.integration.contracts import load_contracts
from concept_to_code_learning.integration.errors import SliceError
from concept_to_code_learning.integration.providers import ProviderConfig, build_providers
from concept_to_code_learning.integration.service import VerticalSliceService
from concept_to_code_learning.integration.store import SnapshotNoteStore
from concept_to_code_learning.store import NoteStore
from concept_to_code_learning.tutor.fixture import FixtureTutor

ROOT = Path(__file__).resolve().parents[2]


class ExplainRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    question: str = Field(min_length=1, max_length=2000)
    document_context: dict
    explanation_level: str


class SaveRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    grounded_explanation_id: str = Field(min_length=1, max_length=100)
    title: str = Field(min_length=1, max_length=160)
    user_text: str = Field(default="", max_length=20000)
    save_requested_by_user: bool


def create_app(data_dir: Path | None = None, root: Path = ROOT, *,
               provider_config: ProviderConfig | None = None) -> FastAPI:
    config = provider_config or ProviderConfig.from_env()
    tutor = FixtureTutor(root)
    storage = data_dir or Path(os.environ.get("C2C_DATA_DIR", root / "data/local"))
    store = NoteStore(storage, tutor.schemas)
    app = FastAPI(title="Concept-to-Code Learning · FIXTURE", version=__version__)
    app.add_middleware(TrustedHostMiddleware,
                       allowed_hosts=["localhost", "127.0.0.1", "[::1]", "testserver"])

    @app.exception_handler(SliceError)
    async def slice_error_handler(request, exc: SliceError):
        return JSONResponse(status_code=exc.http_status, content=exc.payload())

    @app.get("/health")
    def health():
        return {"status": "SCAFFOLD_DEMO", "mode": "FIXTURE", "health": "ok",
                "version": __version__}

    @app.get("/api/demo/session")
    def session():
        return tutor.session()

    @app.post("/api/learning/explain")
    def explain(request: ExplainRequest):
        try:
            response = tutor.explain(request.question.strip(), request.document_context,
                                     request.explanation_level)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
        store.remember(response)
        return response

    @app.post("/api/github/search")
    @app.post("/api/github/verify")
    def not_implemented():
        return JSONResponse(status_code=501, content={
            "mode": "FIXTURE", "status": "SCAFFOLD_DEMO", "code": "NOT_IMPLEMENTED",
            "verification_status": "NEEDS_CONFIRMATION", "results": [],
            "message": "实时搜索与通用核验待实现。本接口没有访问外网。",
        })

    @app.post("/api/notes", status_code=201)
    def save(request: SaveRequest):
        if not request.save_requested_by_user or not request.title.strip():
            raise HTTPException(422, "Explicit user save and a non-empty title are required")
        try:
            return store.save(request.grounded_explanation_id, request.title.strip(),
                              request.user_text)
        except KeyError as exc:
            raise HTTPException(404, "Explanation not found; generate it again") from exc

    @app.get("/api/notes")
    def notes():
        return {"mode": "FIXTURE", "status": "SCAFFOLD_DEMO", "notes": store.list()}

    schemas = load_contracts(root)
    sprint_store = SnapshotNoteStore(store, schemas)
    service = VerticalSliceService(*build_providers(root, config), sprint_store, schemas, config)
    app.include_router(create_router(service, root))

    if (root / "apps/web/dist/index.html").is_file():
        app.mount("/", StaticFiles(directory=root / "apps/web/dist", html=True), name="web")
    return app
