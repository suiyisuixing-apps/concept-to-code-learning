"""Canonical DTOs: JSON Schema and OpenAPI are generated from these models.

Validation establishes shape and internal consistency, never source authenticity.
Only the in-process source provider and the session-bound registry establish trust.
"""

import hashlib
import re
from datetime import datetime, timezone
from pathlib import PurePosixPath
from typing import Annotated, Literal
from urllib.parse import quote
from uuid import uuid4

from pydantic import AfterValidator, AwareDatetime, BaseModel, ConfigDict, Field, model_validator

UTCDate = Annotated[AwareDatetime, AfterValidator(lambda value: value.astimezone(timezone.utc))]

ID = Annotated[str, Field(min_length=1, max_length=200, pattern=r"^[A-Za-z0-9_.:-]+$")]
Hash = Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]
Commit = Annotated[str, Field(pattern=r"^[a-f0-9]{40}$")]
Positive = Annotated[int, Field(ge=1, strict=True)]
Nonnegative = Annotated[int, Field(ge=0, strict=True)]
Mode = Literal["LIVE", "FIXTURE", "UNAVAILABLE"]
Level = Literal["Beginner", "University", "Engineering", "Source-code"]
SourceMode = Literal["specified_public", "public_search", "local_authorized"]
SourceType = Literal["PDF", "PPTX", "DOCX", "MARKDOWN"]
Repo = Annotated[str, Field(pattern=r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$", max_length=200)]
Text = Annotated[str, Field(max_length=100000)]


def uid() -> str:
    return str(uuid4())


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class Value(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_default=True, validate_assignment=True,
                              revalidate_instances="always")


class Record(Value):
    contract_version: Literal["full-delivery-v1"] = "full-delivery-v1"
    revision: Positive = 1
    mode: Mode


class SourceLocator(Value):
    unit_type: Literal["page", "slide", "section"]
    index: Positive
    heading_path: list[str] = Field(default_factory=list, max_length=30)
    block_id: ID | None = None


class Block(Value):
    block_id: ID
    kind: Literal["paragraph", "table", "caption", "code", "formula", "image", "unsupported"]
    text: Text = ""
    source_locator: SourceLocator
    table_rows: list[list[str]] = Field(default_factory=list, max_length=1000)
    bbox: tuple[float, float, float, float] | None = None
    image_asset_id: ID | None = None


class Preview(Value):
    kind: Literal["native_pdf", "learning_view", "image", "unavailable"]
    asset_id: ID | None = None
    fidelity: Literal["original", "extracted", "partial", "unavailable"]
    limitations: list[str] = Field(default_factory=list)


class DocumentRecord(Record):
    document_id: ID
    file_name: Annotated[str, Field(min_length=1, max_length=240)]
    source_type: SourceType
    original_sha256: Hash
    unit_count: Nonnegative
    import_status: Literal["READY", "PARTIAL", "NO_EXTRACTABLE_TEXT", "FAILED"]
    capabilities: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    created_at: UTCDate

    @model_validator(mode="after")
    def display_name_only(self):
        if "/" in self.file_name or "\\" in self.file_name or "\x00" in self.file_name:
            raise ValueError("file_name must be a display name")
        return self


class DocumentUnit(Record):
    document_id: ID
    document_revision: Positive
    unit_id: ID
    unit_type: Literal["page", "slide", "section"]
    index: Positive
    heading_path: list[str] = Field(default_factory=list)
    blocks: list[Block] = Field(default_factory=list, max_length=2000)
    source_locator: SourceLocator
    preview: Preview
    extraction_status: Literal["READY", "PARTIAL", "NO_EXTRACTABLE_TEXT", "UNSUPPORTED"]
    warnings: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def unique_blocks(self):
        if len({b.block_id for b in self.blocks}) != len(self.blocks):
            raise ValueError("Block IDs must be unique in a unit")
        if (self.source_locator.unit_type, self.source_locator.index) != (
                self.unit_type, self.index):
            raise ValueError("Unit locator mismatch")
        return self


class SelectionSpan(Value):
    block_id: ID
    start: Nonnegative
    end: Nonnegative

    @model_validator(mode="after")
    def interval(self):
        if self.end <= self.start:
            raise ValueError("Selection intervals are nonempty and end-exclusive")
        return self


class SelectionLocator(Value):
    spans: list[SelectionSpan] = Field(min_length=1, max_length=50)
    normalization: Literal["exact", "whitespace-v1"] = "exact"


class ContextRequest(Value):
    document_revision: Positive
    unit_id: ID
    selected_text: Annotated[str, Field(max_length=10000)] = ""
    selected_text_hash: Hash | None = None
    selection_locator: SelectionLocator | None = None


class DocumentContext(Record):
    document_id: ID
    document_revision: Positive
    original_sha256: Hash
    source_type: SourceType
    file_name: str
    unit_id: ID
    unit_locator: SourceLocator
    visible_text: Text
    selected_text: Annotated[str, Field(max_length=10000)] = ""
    selected_text_hash: Hash | None = None
    selection_locator: SelectionLocator | None = None
    relevant_context_blocks: list[Block]
    coverage: Literal["TEXT", "PARTIAL", "NO_EXTRACTABLE_TEXT"]
    warnings: list[str] = Field(default_factory=list)
    status: Literal["READY", "PARTIAL", "NO_EXTRACTABLE_TEXT"]

    @model_validator(mode="after")
    def selection_digest(self):
        if self.selected_text_hash != (digest(self.selected_text) if self.selected_text else None):
            raise ValueError("Selection hash mismatch")
        return self


class ScopeLimit(Value):
    repositories: Annotated[int, Field(ge=1, le=20, strict=True)] = 5
    files: Annotated[int, Field(ge=1, le=100, strict=True)] = 10


class SourceScope(Value):
    source_mode: SourceMode = "specified_public"
    repository_allowlist: list[Repo] = Field(default_factory=list, max_length=20)
    local_handle: ID | None = None
    language_hint: Annotated[str, Field(max_length=50)] | None = None
    scope_limit: ScopeLimit = Field(default_factory=ScopeLimit)
    network_authorized: Annotated[bool, Field(strict=True)] = False
    query_terms_approved: Annotated[bool, Field(strict=True)] = False
    auto_public_search: Annotated[bool, Field(strict=True)] = False
    approved_query_terms: list[Annotated[str, Field(min_length=1, max_length=100)]] = Field(
        default_factory=list, max_length=20)
    max_sources: Annotated[int, Field(ge=1, le=3, strict=True)] = 3

    @model_validator(mode="after")
    def local_boundary(self):
        if self.source_mode == "local_authorized" and self.network_authorized:
            raise ValueError("Local scope cannot authorize network transmission")
        return self


class SourceQuery(Record, SourceScope):
    query_id: ID
    question: Annotated[str, Field(min_length=1, max_length=2000)]
    concept_terms: list[Annotated[str, Field(min_length=1, max_length=100)]] = Field(
        min_length=1, max_length=20)
    status: Literal["PLANNED", "AUTHORIZED", "NEEDS_CONFIRMATION"]


class SearchCandidate(Record):
    candidate_id: ID
    query_id: ID
    source_mode: SourceMode
    repository: Repo | None = None
    local_handle: ID | None = None
    ref_hint: str | None = None
    file_hint: str | None = None
    symbol_hint: str | None = None
    matched_terms: list[str]
    ranking_reason: Annotated[str, Field(min_length=1, max_length=2000)]
    discovery_method: str
    discovery_status: Literal["CANDIDATE", "NEEDS_CONFIRMATION", "REJECTED"]
    retrieved_at: UTCDate


class SearchResult(Record):
    query_id: ID
    candidates: list[SearchCandidate]
    selection_required: Annotated[bool, Field(strict=True)] = False
    status: Literal["CANDIDATES", "NO_RELEVANT_SOURCE", "NEEDS_CONFIRMATION"]
    warnings: list[str] = Field(default_factory=list)


class LicenseFile(Value):
    path: str
    commit_sha: Commit | None = None
    content_sha256: Hash
    permalink: str | None = None
    identifier: str | None = None


class LicenseObservation(Value):
    status: Literal["DETECTED", "UNKNOWN", "MIXED"]
    files: list[LicenseFile] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    code_display_allowed: Annotated[bool, Field(strict=True)] = False


class Relevance(Value):
    status: Literal["SUPPORTED", "CANDIDATE", "UNCERTAIN", "NOT_RELEVANT"]
    reason: Annotated[str, Field(min_length=1, max_length=2000)]
    basis: list[str] = Field(default_factory=list)


class CodeEvidence(Record):
    source_id: ID
    source_mode: SourceMode
    repository_owner: str | None = None
    repository_name: str | None = None
    repository_url: str | None = None
    visibility: Literal["public", "local"]
    local_handle: ID | None = None
    dirty: Annotated[bool, Field(strict=True)] = False
    commit_sha: Commit | None = None
    requested_ref: str | None = None
    file_path: Annotated[str, Field(min_length=1, max_length=1000)]
    language: str
    symbol: str | None = None
    symbol_kind: str | None = None
    line_start: Positive
    line_end: Positive
    code_excerpt: Annotated[str, Field(max_length=20000)]
    excerpt_sha256: Hash
    file_blob_sha: Commit | None = None
    file_sha256: Hash | None = None
    permalink: str | None = None
    license_observation: LicenseObservation
    retrieved_at: UTCDate
    verification_checks: dict[str, Literal["PASSED", "FAILED", "NOT_APPLICABLE", "NOT_CHECKED"]]
    provenance_kind: Literal["SOURCE_EXACT", "ADAPTED_FROM_SOURCE", "AI_GENERATED"]
    verification_status: Literal["VERIFIED", "UNVERIFIED", "NEEDS_CONFIRMATION", "REJECTED"]
    execution_status: Literal["NOT_RUN", "RUN_PASSED", "RUN_FAILED", "BLOCKED"] = "NOT_RUN"
    relevance: Relevance

    @model_validator(mode="after")
    def consistent_evidence(self):
        path = PurePosixPath(self.file_path)
        if path.is_absolute() or ".." in path.parts or "\\" in self.file_path:
            raise ValueError("Source paths must be repository-relative")
        if self.line_end < self.line_start or digest(self.code_excerpt) != self.excerpt_sha256:
            raise ValueError("Source range or hash mismatch")
        if self.code_excerpt and self.line_end - self.line_start + 1 != len(
                self.code_excerpt.splitlines()):
            raise ValueError("Excerpt line count mismatch")
        license = self.license_observation
        if self.code_excerpt and (not license.code_display_allowed or license.status != "DETECTED"):
            raise ValueError("Unknown or mixed license must withhold code by default")
        if license.status == "DETECTED" and not license.files:
            raise ValueError("License detection requires observed files")
        if self.source_mode != "local_authorized":
            expected_repo = f"https://github.com/{self.repository_owner}/{self.repository_name}"
            expected_link = (f"{expected_repo}/blob/{self.commit_sha}/"
                             f"{quote(self.file_path, safe='/')}#L{self.line_start}-L{self.line_end}")
            if (self.visibility != "public" or not self.commit_sha
                    or self.repository_url != expected_repo or self.permalink != expected_link):
                raise ValueError("Public evidence requires an immutable GitHub permalink")
            if self.local_handle or self.dirty:
                raise ValueError("Public evidence is a committed public file")
        elif not self.local_handle or self.visibility != "local":
            raise ValueError("Local evidence requires an authorized handle")
        elif self.dirty and (not self.file_sha256 or self.permalink is not None):
            raise ValueError("Dirty local bytes require a content hash and no exact web permalink")
        if self.repository_url is not None:
            identity = f"{self.repository_owner}/{self.repository_name}"
            if (not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", identity)
                    or self.repository_url != f"https://github.com/{identity}"):
                raise ValueError("Repository links must use a canonical GitHub identity")
        if self.source_mode == "local_authorized" and self.permalink is not None:
            expected = (f"{self.repository_url}/blob/{self.commit_sha}/"
                        f"{quote(self.file_path, safe='/')}#L{self.line_start}-L{self.line_end}")
            if (not self.repository_url or not self.commit_sha or self.permalink != expected
                    or self.verification_checks.get("public_remote") != "PASSED"):
                raise ValueError("A local web permalink requires a verified public remote and exact commit")
        if self.verification_status == "VERIFIED" and not (
                self.file_blob_sha or self.file_sha256):
            raise ValueError("Verified evidence requires a file identity")
        return self


class TeachingPlan(Record):
    plan_id: ID
    question: Annotated[str, Field(min_length=1, max_length=2000)]
    level: Level
    concepts: list[str]
    prerequisites: list[str] = Field(default_factory=list)
    needs_code: Annotated[bool, Field(strict=True)]
    source_query: SourceQuery | None = None
    uncertainties: list[str] = Field(default_factory=list)
    status: Literal["READY", "NEEDS_CONFIRMATION"]


class AnswerSection(Value):
    title: Annotated[str, Field(min_length=1, max_length=200)]
    text: Annotated[str, Field(min_length=1, max_length=20000)]


class DocumentCitation(Value):
    block_id: ID
    quote: Annotated[str, Field(min_length=1, max_length=10000)]
    quote_sha256: Hash


class ConceptCodeLink(Value):
    concept: str
    source_id: ID
    symbol: str | None = None
    reason: Annotated[str, Field(min_length=1, max_length=2000)]


class ExampleBlock(Value):
    provenance_kind: Literal["SOURCE_EXACT", "ADAPTED_FROM_SOURCE", "AI_GENERATED"]
    source_id: ID | None = None
    language: str
    code: Annotated[str, Field(max_length=20000)]
    explanation: str
    execution_status: Literal["NOT_RUN", "RUN_PASSED", "RUN_FAILED", "BLOCKED"] = "NOT_RUN"


class Comparison(Value):
    source_ids: list[ID] = Field(min_length=2, max_length=3)
    summary: str
    tradeoffs: list[str]


class ProviderInfo(Value):
    provider_id: ID
    model_id: str | None = None
    mode: Mode
    endpoint_kind: Literal["loopback", "authorized_remote", "fixture", "unavailable"]
    status: Literal["AVAILABLE", "UNAVAILABLE", "FIXTURE"]


class Metrics(Value):
    latency_ms: float = Field(ge=0, allow_inf_nan=False)
    input_tokens: Nonnegative | None = None
    output_tokens: Nonnegative | None = None
    token_source: Literal["PROVIDER_USAGE", "ESTIMATE", "UNAVAILABLE"] = "UNAVAILABLE"
    input_truncated: Annotated[bool, Field(strict=True)] = False
    truncation_reason: str | None = None

    @model_validator(mode="after")
    def usage_attribution(self):
        counts = (self.input_tokens, self.output_tokens)
        if self.token_source == "UNAVAILABLE" and any(value is not None for value in counts):
            raise ValueError("Unavailable usage cannot contain invented token counts")
        if self.token_source != "UNAVAILABLE" and all(value is None for value in counts):
            raise ValueError("Attributed usage requires counts")
        return self


class GroundedExplanation(Record):
    explanation_id: ID
    question: str
    context_snapshot: DocumentContext
    level: Level
    answer_sections: list[AnswerSection] = Field(min_length=1, max_length=20)
    document_citations: list[DocumentCitation] = Field(default_factory=list, max_length=100)
    code_source_ids: list[ID] = Field(default_factory=list, max_length=3)
    concept_code_links: list[ConceptCodeLink] = Field(default_factory=list)
    example_blocks: list[ExampleBlock] = Field(default_factory=list)
    comparison: Comparison | None = None
    limitations: list[str] = Field(default_factory=list)
    unsupported_claims: list[str] = Field(default_factory=list)
    provider_info: ProviderInfo
    metrics: Metrics
    status: Literal["GROUNDED", "NO_VERIFIED_CODE", "FIXTURE"]


class ExplanationRequest(Value):
    request_id: ID = Field(default_factory=uid)
    session_id: ID
    context_revision: Positive
    question: Annotated[str, Field(min_length=1, max_length=2000)]
    level: Level = "Beginner"
    scope: SourceScope = Field(default_factory=SourceScope)
    source_ids: list[ID] = Field(default_factory=list, max_length=3)
    candidate_ids: list[ID] = Field(default_factory=list, max_length=10)
    query_id: ID | None = None
    compare: Annotated[bool, Field(strict=True)] = False
    continue_from: ID | None = None
    model_id: Annotated[str, Field(min_length=1, max_length=1000)] | None = None
    model_base_url: Annotated[str, Field(min_length=1, max_length=500)] | None = None


class ExplanationResult(Record):
    request_id: ID
    session_id: ID
    context_revision: Positive
    status: Literal["COMPLETE", "NEEDS_SOURCE_SELECTION"]
    explanation: GroundedExplanation | None = None
    sources: list[CodeEvidence] = Field(default_factory=list)
    source_observations: list[CodeEvidence] = Field(default_factory=list, max_length=3)
    candidates: list[SearchCandidate] = Field(default_factory=list)
    query_id: ID | None = None
    warnings: list[str] = Field(default_factory=list)


class SessionRecord(Record):
    session_id: ID
    context_revision: Nonnegative
    context: DocumentContext | None = None
    explanation_ids: list[ID] = Field(default_factory=list)
    status: Literal["EMPTY", "READY"]
    created_at: UTCDate


class ActivateContext(ContextRequest):
    document_id: ID
    expected_context_revision: Nonnegative


class SearchRequest(Value):
    session_id: ID
    context_revision: Positive
    question: Annotated[str, Field(min_length=1, max_length=2000)]
    concept_terms: list[Annotated[str, Field(min_length=1, max_length=100)]] = Field(
        min_length=1, max_length=20)
    scope: SourceScope


class VerifyRequest(Value):
    session_id: ID
    query_id: ID
    candidate_id: ID


class SaveNoteRequest(Value):
    session_id: ID
    explanation_id: ID
    idempotency_key: ID
    save_requested_by_user: Annotated[bool, Field(strict=True)]
    title: Annotated[str, Field(min_length=1, max_length=160)]
    user_text: Annotated[str, Field(max_length=20000)] = ""


class EditNoteRequest(Value):
    expected_revision: Positive
    title: Annotated[str, Field(min_length=1, max_length=160)]
    user_text: Annotated[str, Field(max_length=20000)]


class DeleteNoteRequest(Value):
    expected_revision: Positive
    confirmed_by_user: Annotated[bool, Field(strict=True)]


class SavedNote(Record):
    note_id: ID
    title: str
    user_text: str
    explanation_snapshot: GroundedExplanation
    document_snapshot: DocumentContext
    code_evidence_snapshot: list[CodeEvidence]
    snapshot_sha256: Hash
    created_at: UTCDate
    updated_at: UTCDate
    status: Literal["SAVED"] = "SAVED"


class NoteList(Record):
    notes: list[SavedNote]
    total: Nonnegative
    offset: Nonnegative
    status: Literal["READY"] = "READY"


class ProviderCapability(Value):
    provider_id: ID
    implemented: Annotated[bool, Field(strict=True)]
    available: Annotated[bool, Field(strict=True)]
    mode: Mode
    features: list[str]
    status: Literal["AVAILABLE", "UNAVAILABLE", "FIXTURE"]
    reason_code: str | None = None
    needed_action: str | None = None
    data_flow: list[str] = Field(default_factory=list)


class Capabilities(Record):
    capability_id: ID = "learning-v1"
    document: ProviderCapability
    sources: ProviderCapability
    tutor: ProviderCapability
    persistent_notes: bool = True
    legacy_readable: bool = True
    integrated_product: Literal["UNAVAILABLE", "FIXTURE", "READY_FOR_LIVE_CHECK"]
    target_hardware: Literal["NOT_TESTED"] = "NOT_TESTED"
    lead_review: Literal["PENDING"] = "PENDING"
    status: Literal["PARTIAL", "AVAILABLE", "FIXTURE"]


class LearningErrorResponse(Value):
    contract_version: Literal["full-delivery-v1"] = "full-delivery-v1"
    request_id: ID
    stage: str
    code: str
    user_message: str
    retryable: bool
    needed_action: str | None = None


class DocumentList(Record):
    documents: list[DocumentRecord]
    status: Literal["READY"] = "READY"


class UnitList(Record):
    document_id: ID
    units: list[DocumentUnit]
    status: Literal["READY"] = "READY"
