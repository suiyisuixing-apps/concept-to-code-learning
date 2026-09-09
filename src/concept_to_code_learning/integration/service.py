"""Fail-closed orchestration; teammates replace the ports, not the public contracts."""

import re
from copy import deepcopy

from concept_to_code_learning.integration.contracts import require, validate
from concept_to_code_learning.integration.errors import SliceError
from concept_to_code_learning.integration.ports import (
    SOURCE_CHECKS,
    DocumentContextProvider,
    DocumentSelection,
    GitHubSourceVerifier,
    GroundedTutorProvider,
    NoteStore,
    SourceRequest,
    VerifiedSource,
)
from concept_to_code_learning.integration.providers import ProviderConfig


class VerticalSliceService:
    def __init__(self, document: DocumentContextProvider, github: GitHubSourceVerifier,
                 tutor: GroundedTutorProvider, notes: NoteStore, schemas: dict,
                 config: ProviderConfig):
        self.document, self.github, self.tutor = document, github, tutor
        self.notes, self.schemas, self.config = notes, schemas, config

    @staticmethod
    def call(stage, action, *args):
        try:
            return action(*args)
        except SliceError:
            raise
        except Exception as exc:
            raise SliceError("PROVIDER_UNAVAILABLE", stage,
                             "Provider failed; no fallback was attempted", 503) from exc

    def context(self, selection: DocumentSelection) -> dict:
        context = deepcopy(self.call("document", self.document.resolve, selection))
        validate("document-context", context, self.schemas)
        require(context["document_id"] == selection.document_id
                and context["current_slide"] == selection.current_slide
                and context["current_page"] == selection.current_page
                and context["selected_text"] == selection.selected_text,
                "INVALID_PROVIDER_RESPONSE", "document", "Document provider changed the selection")
        require(context["mode"] == ("FIXTURE" if self.config.document == "fixture" else "LIVE"),
                "INVALID_PROVIDER_RESPONSE", "document", "Document provider mode does not match")
        return context

    def verify(self, request: SourceRequest) -> dict:
        if self.config.github == "github":
            require(request.network_authorized is True, "NETWORK_NOT_AUTHORIZED", "github",
                    "Explicit authorization for the selected public repository is required")
        result = self.call("github", self.github.verify, request)
        require(isinstance(result, VerifiedSource) and result.request == request
                and isinstance(result.checks, frozenset) and SOURCE_CHECKS <= result.checks,
                "SOURCE_UNVERIFIED", "github",
                "A matching server-side verification receipt with all checks is required")
        source = deepcopy(result.source)
        validate("github-code-source", source, self.schemas)
        require(source["verification_status"] == "GITHUB_SOURCE_VERIFIED",
                "SOURCE_UNVERIFIED", "github", "Source has not passed verification")
        require(source["repository_url"] == request.repository_url
                and source["file_path"] == request.file_path
                and (request.symbol is None or source["symbol"] == request.symbol),
                "SOURCE_UNVERIFIED", "github", "Verifier returned a different source")
        if re.fullmatch(r"[a-f0-9]{40}", request.ref_or_commit):
            require(source["commit_sha"] == request.ref_or_commit, "SOURCE_UNVERIFIED", "github",
                    "Verifier returned a different commit")
        else:
            require(source["branch_or_tag"] == request.ref_or_commit, "SOURCE_UNVERIFIED", "github",
                    "Verifier did not record the requested ref")
        require(source["mode"] == ("FIXTURE" if self.config.github == "fixture" else "LIVE"),
                "INVALID_PROVIDER_RESPONSE", "github", "GitHub provider mode does not match")
        return source

    def explain(self, selection: DocumentSelection, source_request: SourceRequest,
                question: str, level: str) -> dict:
        require(isinstance(question, str) and 0 < len(question.strip()) <= 2000
                and level in {"Beginner", "University"}, "INVALID_QUESTION", "request",
                "Provide a question and Beginner or University level")
        context = self.context(selection)
        source = self.verify(source_request)
        question = question.strip()
        answer = deepcopy(self.call("tutor", self.tutor.explain, deepcopy(context),
                                    deepcopy(source), question, level))
        validate("grounded-explanation", answer, self.schemas)
        require(answer["document_context"] == context and answer["github_sources"] == [source]
                and answer["question"] == question and answer["explanation_level"] == level
                and answer["provider_mode"] == self.config.tutor, "INVALID_PROVIDER_RESPONSE",
                "tutor", "Tutor changed the request, verified sources or provider identity")
        self.call("storage", self.notes.remember, deepcopy(answer))
        return answer

    def save_note(self, explanation_id: str, title: str, user_text: str,
                  save_requested_by_user: bool) -> dict:
        return self.call("storage", self.notes.save, explanation_id, title, user_text,
                         save_requested_by_user)
