"""Versioned schema checks and cross-field invariants; no remote schema resolution."""

import hashlib
import json
import re
from pathlib import Path, PurePosixPath

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError, ValidationError

from concept_to_code_learning.contracts import FORMATS
from concept_to_code_learning.integration.errors import SliceError
from concept_to_code_learning.legacy_contracts import _local_references_only

NAMES = ("document-context", "github-code-source", "grounded-explanation", "saved-note")


def digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_contracts(root: Path) -> dict:
    schemas = {}
    for name in NAMES:
        try:
            schema = json.loads((root / "schemas/sprint-1" / f"{name}.schema.json").read_text())
            _local_references_only(schema)
            Draft202012Validator.check_schema(schema)
            schemas[name] = schema
        except (OSError, ValueError, SchemaError) as exc:
            raise SliceError("INVALID_CONTRACT", "configuration",
                             f"Cannot load Sprint 1 contract: {name}", 500) from exc
    return schemas


def require(condition: bool, code: str, stage: str, message: str) -> None:
    if not condition:
        raise SliceError(code, stage, message)


def validate(name: str, record: dict, schemas: dict) -> None:
    try:
        Draft202012Validator(schemas[name], format_checker=FORMATS).validate(record)
    except ValidationError as exc:
        location = ".".join(map(str, exc.absolute_path)) or "<root>"
        # Do not echo model output, private document text or local paths in errors.
        raise SliceError("INVALID_CONTRACT", name, f"Invalid field: {location}") from exc
    if name == "document-context":
        selected = record["selected_text"]
        require(bool(record["visible_text"].strip()), "NO_VISIBLE_TEXT", "document",
                "The current page or slide contains no visible text")
        require(not selected or selected in record["visible_text"], "SELECTION_MISMATCH",
                "document", "Selection does not belong to the current page or slide")
        require(record["selected_text_hash"] == (digest(selected) if selected else None),
                "SELECTION_MISMATCH", "document", "Selection hash does not match")
    elif name == "github-code-source":
        if record["verification_status"] == "GITHUB_SOURCE_VERIFIED":
            start, end = record["line_start"], record["line_end"]
            require(end >= start and end - start + 1 == len(record["code_excerpt"].splitlines()),
                    "SOURCE_UNVERIFIED", "github", "Source line interval does not match excerpt")
            require(digest(record["code_excerpt"]) == record["excerpt_hash"],
                    "SOURCE_UNVERIFIED", "github", "Source excerpt hash does not match")
            path = record["file_path"]
            require(not PurePosixPath(path).is_absolute() and ".." not in path.split("/")
                    and "\\" not in path and path.endswith(".py"), "SOURCE_REJECTED",
                    "github", "Sprint 1 requires a relative Python source path")
            owner, repo = record["repository_owner"], record["repository_name"]
            require(bool(re.fullmatch(r"[A-Za-z0-9_.-]+", owner))
                    and bool(re.fullmatch(r"[A-Za-z0-9_.-]+", repo))
                    and record["repository_url"] == f"https://github.com/{owner}/{repo}",
                    "SOURCE_UNVERIFIED", "github", "Repository identity does not match")
    elif name == "grounded-explanation":
        context = record["document_context"]
        validate("document-context", context, schemas)
        require(record["concept"]["document_context"] == context, "GROUNDING_INCOMPLETE",
                "tutor", "Concept is bound to a different document context")
        for citation in record["document_citations"]:
            fields = {"document_id": "document_id", "file_name": "file_name",
                      "source_type": "source_type", "file_hash": "file_hash",
                      "page": "current_page", "slide": "current_slide",
                      "section": "current_section"}
            require(all(citation[key] == context[value] for key, value in fields.items())
                    and citation["quote"] in context["visible_text"]
                    and citation["quote_hash"] == digest(citation["quote"]),
                    "GROUNDING_INCOMPLETE", "tutor", "Document citation is not grounded")
        for source in record["github_sources"]:
            validate("github-code-source", source, schemas)
            require(source["verification_status"] == "GITHUB_SOURCE_VERIFIED",
                    "SOURCE_UNVERIFIED", "tutor", "Explanation requires a verified source")
        if record["unsupported_claims"]:
            raise SliceError("GROUNDING_INCOMPLETE", "tutor",
                             "Provider reported unsupported claims; explanation was not accepted",
                             details={"unsupported_claims": record["unsupported_claims"],
                                      "unresolved_items": record["unresolved_items"]})
        all_live = context["mode"] == "LIVE" and all(
            source["mode"] == "LIVE" for source in record["github_sources"]
        ) and record["provider_mode"] == "openai_compatible"
        expected = ("LIVE", "GROUNDED_ANSWER") if all_live else ("FIXTURE", "SCAFFOLD_DEMO")
        require((record["mode"], record["status"]) == expected, "INVALID_PROVIDER_RESPONSE",
                "tutor", "Response mode must reflect every provider's actual mode")
        require(not all_live or not record["unresolved_items"], "GROUNDING_INCOMPLETE",
                "tutor", "Unresolved grounding prevents a completed live answer")
    elif name == "saved-note":
        snapshot = record["explanation_snapshot"]
        validate("grounded-explanation", snapshot, schemas)
        require(record["grounded_explanation"] == snapshot
                and record["grounded_explanation_id"] == snapshot["grounded_explanation_id"]
                and record["document_sources"] == snapshot["document_citations"]
                and record["github_sources"] == snapshot["github_sources"]
                and record["mode"] == snapshot["mode"]
                and record["status"] == snapshot["status"],
                "INVALID_CONTRACT", "note", "Note and explanation snapshots must agree")
