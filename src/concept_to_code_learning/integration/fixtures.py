"""Adapters for the existing synthetic lesson and manually verified frozen source."""

import hashlib
from copy import deepcopy
from pathlib import Path

from concept_to_code_learning.integration.contracts import require
from concept_to_code_learning.integration.errors import SliceError
from concept_to_code_learning.integration.ports import (
    SOURCE_CHECKS,
    DocumentSelection,
    DocumentUpload,
    SourceRequest,
    VerifiedSource,
)
from concept_to_code_learning.tutor.fixture import FixtureTutor


class FixtureDocumentProvider:
    def __init__(self, root: Path, fixture: FixtureTutor):
        self.fixture = fixture
        # Fixture content is this JSON file, not an invented PPTX or the display filename.
        self.file_hash = hashlib.sha256((root / "demo/learning/document.json").read_bytes()
                                       ).hexdigest()

    def import_document(self, upload: DocumentUpload) -> dict:
        raise SliceError("PROVIDER_NOT_IMPLEMENTED", "document",
                         "Fixture mode cannot import a real document", 501)

    def resolve(self, selection: DocumentSelection) -> dict:
        require(selection.document_id == self.fixture.document["document_id"],
                "DOCUMENT_NOT_FOUND", "document", "Unknown fixture document")
        page = selection.current_page
        require(type(page) is int and 1 <= page <= len(self.fixture.document["pages"])
                and selection.current_slide is None, "INVALID_SLIDE", "document",
                "Fixture requires an existing synthetic page, not a PPTX slide")
        context = self.fixture.context(page, selection.selected_text)
        return {**context, "contract_version": "sprint-1", "file_hash": self.file_hash,
                "visible_text": "\n\n".join(self.fixture.document["pages"][page - 1]["paragraphs"]),
                "mode": "FIXTURE"}


class FixtureGitHubVerifier:
    def __init__(self, fixture: FixtureTutor):
        self.fixture = fixture

    def verify(self, request: SourceRequest) -> VerifiedSource:
        source = self.fixture.source
        require(request.repository_url == source["repository_url"]
                and request.ref_or_commit == source["commit_sha"]
                and request.file_path == source["file_path"]
                and request.symbol in (None, source["symbol"]), "SOURCE_NOT_FOUND", "github",
                "Fixture only supports its declared repository, commit, file and symbol")
        return VerifiedSource({**deepcopy(source), "contract_version": "sprint-1"},
                              request, SOURCE_CHECKS)


class FixtureGroundedTutor:
    def __init__(self, fixture: FixtureTutor):
        self.fixture = fixture

    def explain(self, context: dict, source: dict, question: str, level: str) -> dict:
        # Do not silently substitute the fixed lesson for real teammate data.
        legacy_context = {key: context[key] for key in self.fixture.context()}
        require(source == {**self.fixture.source, "contract_version": "sprint-1"}
                and context["mode"] == "FIXTURE", "FIXTURE_INPUT_UNSUPPORTED", "tutor",
                "This fixed explanation only supports the declared fixture lesson and source")
        try:
            answer = self.fixture.explain(question, legacy_context, level)
        except ValueError as exc:
            raise SliceError("FIXTURE_INPUT_UNSUPPORTED", "tutor",
                             "Fixture supports only its dependency-injection lesson") from exc
        answer.update(contract_version="sprint-1", provider_mode="fixture", unsupported_claims=[])
        answer["document_context"] = deepcopy(context)
        answer["concept"]["document_context"] = deepcopy(context)
        answer["github_sources"] = [deepcopy(source)]
        for citation in answer["document_citations"]:
            citation["file_hash"] = context["file_hash"]
        return answer
