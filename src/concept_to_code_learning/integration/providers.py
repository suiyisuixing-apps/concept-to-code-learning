"""Explicit provider selection. Unimplemented providers never fall back or make requests."""

import os
from dataclasses import dataclass
from urllib.parse import urlsplit

from concept_to_code_learning.integration.errors import SliceError
from concept_to_code_learning.integration.fixtures import (
    FixtureDocumentProvider,
    FixtureGitHubVerifier,
    FixtureGroundedTutor,
)
from concept_to_code_learning.integration.ports import DocumentSelection, SourceRequest
from concept_to_code_learning.tutor.fixture import FixtureTutor


@dataclass(frozen=True)
class ProviderConfig:
    document: str = "fixture"
    github: str = "fixture"
    tutor: str = "fixture"
    tutor_base_url: str = ""
    tutor_model: str = ""

    def __post_init__(self):
        for value, allowed in ((self.document, {"fixture", "pptx"}),
                               (self.github, {"fixture", "github"}),
                               (self.tutor, {"fixture", "openai_compatible"})):
            if value not in allowed:
                raise SliceError("INVALID_PROVIDER", "configuration",
                                 "Unknown provider; select one of the documented modes", 503)

    @classmethod
    def from_env(cls, env=None):
        env = os.environ if env is None else env
        return cls(env.get("DOCUMENT_PROVIDER", "fixture"),
                   env.get("GITHUB_SOURCE_PROVIDER", "fixture"),
                   env.get("TUTOR_PROVIDER", "fixture"),
                   env.get("TUTOR_BASE_URL", ""), env.get("TUTOR_MODEL", ""))

    def public_modes(self) -> dict:
        return {"document": self.document, "github": self.github, "tutor": self.tutor}


class UnavailableProvider:
    def __init__(self, stage: str, config: ProviderConfig):
        self.stage = stage
        self.config = config

    def fail(self):
        if self.stage == "tutor":
            try:
                parsed = urlsplit(self.config.tutor_base_url)
                configured = (parsed.scheme in {"http", "https"} and parsed.hostname
                              and not parsed.username and not parsed.password
                              and self.config.tutor_model.strip())
            except ValueError:
                configured = False
            if not configured:
                raise SliceError("PROVIDER_NOT_CONFIGURED", "tutor",
                                 "Set an authorized TUTOR_BASE_URL and TUTOR_MODEL", 503)
        raise SliceError("PROVIDER_NOT_IMPLEMENTED", self.stage,
                         "The selected real provider is awaiting its owner's implementation", 501)

    def import_document(self, upload):
        self.fail()

    def resolve(self, selection):
        self.fail()

    def verify(self, request):
        self.fail()

    def explain(self, context, source, question, level):
        self.fail()


def build_providers(root, config: ProviderConfig):
    fixture = FixtureTutor(root)
    document = FixtureDocumentProvider(root, fixture) if config.document == "fixture" else (
        UnavailableProvider("document", config))
    github = FixtureGitHubVerifier(fixture) if config.github == "fixture" else (
        UnavailableProvider("github", config))
    tutor = FixtureGroundedTutor(fixture) if config.tutor == "fixture" else (
        UnavailableProvider("tutor", config))
    return document, github, tutor


def fixture_request(root) -> dict:
    """An honest, discoverable offline example, never a default for arbitrary user input."""
    from dataclasses import asdict

    from concept_to_code_learning.tutor.fixture import QUESTION

    fixture = FixtureTutor(root)
    source = fixture.source
    return {"question": QUESTION, "explanation_level": "Beginner",
            "document": asdict(DocumentSelection(fixture.document["document_id"], current_page=1)),
            "source": asdict(SourceRequest(source["repository_url"], source["commit_sha"],
                                           source["file_path"], source["symbol"]))}
