"""Versioned integration API. Real upload/slide handlers remain Document-owned stubs."""

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict, Field, StrictBool

from concept_to_code_learning.integration.errors import SliceError
from concept_to_code_learning.integration.ports import DocumentSelection, SourceRequest
from concept_to_code_learning.integration.providers import fixture_request


class SelectionBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    document_id: str = Field(min_length=1, max_length=200)
    current_slide: int | None = Field(default=None, ge=1, strict=True)
    current_page: int | None = Field(default=None, ge=1, strict=True)
    selected_text: str = Field(default="", max_length=10000)


class SourceBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    repository_url: str = Field(min_length=1, max_length=500)
    ref_or_commit: str = Field(min_length=1, max_length=200)
    file_path: str = Field(min_length=1, max_length=1000)
    symbol: str | None = Field(default=None, min_length=1, max_length=300)
    network_authorized: StrictBool = False


class ExplainBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    question: str = Field(min_length=1, max_length=2000)
    explanation_level: str
    document: SelectionBody
    source: SourceBody


class SaveBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    grounded_explanation_id: str = Field(min_length=1, max_length=100)
    title: str = Field(min_length=1, max_length=160)
    user_text: str = Field(default="", max_length=20000)
    save_requested_by_user: StrictBool


def create_router(service, root) -> APIRouter:
    router = APIRouter(prefix="/api/sprint-1", tags=["Sprint 1 integration"])

    @router.get("/session")
    def session():
        modes = service.config.public_modes()
        return {"contract_version": "sprint-1", "providers": modes,
                "status": "SCAFFOLD_DEMO" if all(v == "fixture" for v in modes.values())
                else "PROVIDERS_UNAVAILABLE",
                "capabilities": {"real_pptx": False, "live_github": False, "model": False,
                                 "fixture_integration": True, "persistent_notes": True},
                "fixture_example": fixture_request(root)}

    @router.post("/documents", status_code=501)
    @router.get("/documents/{document_id}/slides/{slide}", status_code=501)
    def documents_not_implemented():
        raise SliceError("PROVIDER_NOT_IMPLEMENTED", "document",
                         "Real PPTX upload and slide reading await the Document PR", 501)

    @router.post("/documents/context")
    def context(request: SelectionBody):
        return service.context(DocumentSelection(**request.model_dump()))

    @router.post("/github/verify")
    def verify(request: SourceBody):
        # Returned metadata is informational. Explain re-verifies from the original input;
        # it never accepts this payload as an authoritative client-provided receipt.
        return service.verify(SourceRequest(**request.model_dump()))

    @router.post("/learning/explain")
    def explain(request: ExplainBody):
        return service.explain(DocumentSelection(**request.document.model_dump()),
                               SourceRequest(**request.source.model_dump()),
                               request.question, request.explanation_level)

    @router.post("/notes", status_code=201)
    def save(request: SaveBody):
        return service.save_note(request.grounded_explanation_id, request.title,
                                 request.user_text, request.save_requested_by_user)

    @router.get("/notes")
    def notes():
        return {"contract_version": "sprint-1", "notes": service.notes.list()}

    return router
