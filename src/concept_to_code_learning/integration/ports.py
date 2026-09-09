"""Server-side ports. Verification receipts must never be accepted from HTTP clients."""

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class DocumentUpload:
    file_name: str
    content: bytes


@dataclass(frozen=True)
class DocumentSelection:
    document_id: str
    selected_text: str = ""
    current_slide: int | None = None
    current_page: int | None = None


@dataclass(frozen=True)
class SourceRequest:
    repository_url: str
    ref_or_commit: str
    file_path: str
    symbol: str | None = None
    network_authorized: bool = False


# The verifier owns these checks. The service checks completeness and source binding;
# a receipt is a trusted in-process assertion, not independent proof of a network fetch.
SOURCE_CHECKS = frozenset({"public_repository", "commit", "file", "python_symbol",
                           "line_range", "excerpt_hash", "license"})


@dataclass(frozen=True)
class VerifiedSource:
    source: dict
    request: SourceRequest
    checks: frozenset[str]


class DocumentContextProvider(Protocol):
    def import_document(self, upload: DocumentUpload) -> dict: ...

    def resolve(self, selection: DocumentSelection) -> dict: ...


class GitHubSourceVerifier(Protocol):
    def verify(self, request: SourceRequest) -> VerifiedSource: ...


class GroundedTutorProvider(Protocol):
    def explain(self, context: dict, source: dict, question: str, level: str) -> dict: ...


class NoteStore(Protocol):
    def remember(self, explanation: dict) -> None: ...

    def save(self, explanation_id: str, title: str, user_text: str,
             save_requested_by_user: bool) -> dict: ...

    def list(self) -> list[dict]: ...
