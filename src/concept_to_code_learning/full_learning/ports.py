"""Member-owned providers implement these async in-process interfaces.

Factories are installed by the Lead, never supplied by an HTTP request. A receipt
is an assertion by that trusted implementation, not proof supplied by a browser.
Providers must be cancellable and must not execute fetched repository contents.
"""

from dataclasses import dataclass
from typing import Protocol

from concept_to_code_learning.full_contracts.models import (
    CodeEvidence,
    DocumentContext,
    DocumentRecord,
    DocumentUnit,
    GroundedExplanation,
    Level,
    ProviderCapability,
    SearchCandidate,
    SearchResult,
    SourceQuery,
    TeachingPlan,
)


@dataclass(frozen=True)
class DocumentUpload:
    file_name: str
    content: bytes


@dataclass(frozen=True)
class DocumentAsset:
    content: bytes
    media_type: str
    file_name: str


@dataclass(frozen=True)
class VerificationReceipt:
    query_id: str
    candidate_id: str
    scope_sha256: str
    evidence: CodeEvidence


class HealthProvider(Protocol):
    async def capabilities(self) -> ProviderCapability: ...
    async def close(self) -> None: ...


class DocumentProvider(HealthProvider, Protocol):
    async def import_document(self, upload: DocumentUpload) -> DocumentRecord: ...
    async def list_documents(self) -> list[DocumentRecord]: ...
    async def get_document(self, document_id: str) -> DocumentRecord: ...
    async def list_units(self, document_id: str) -> list[DocumentUnit]: ...
    async def get_unit(self, document_id: str, unit_id: str) -> DocumentUnit: ...
    async def get_asset(self, document_id: str, asset_id: str) -> DocumentAsset: ...


class SourceProvider(HealthProvider, Protocol):
    async def search(self, query: SourceQuery) -> SearchResult: ...
    async def verify(self, query: SourceQuery, candidate: SearchCandidate,
                     scope_sha256: str) -> VerificationReceipt: ...
    # Host-authorized handles are configured outside HTTP. No arbitrary path endpoint.
    async def local_handles(self) -> list[str]: ...


class TutorProvider(HealthProvider, Protocol):
    async def plan(self, context: DocumentContext, question: str, level: Level,
                   conversation: list[GroundedExplanation]) -> TeachingPlan: ...
    async def explain(self, context: DocumentContext, verified_sources: list[CodeEvidence],
                      plan: TeachingPlan, conversation: list[GroundedExplanation],
                      *, compare: bool = False) -> GroundedExplanation: ...


@dataclass(frozen=True)
class ProviderBundle:
    document: DocumentProvider
    sources: SourceProvider
    tutor: TutorProvider
