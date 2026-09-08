"""Six active contracts. Validation is local; schema references never fetch URLs."""

import json
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit

from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import SchemaError, ValidationError

from concept_to_code_learning.legacy_contracts import _local_references_only

SCHEMA_NAMES = (
    "document-context", "learning-concept", "github-code-source",
    "grounded-explanation", "saved-note", "runnable-example",
)
FORMATS = FormatChecker()


@FORMATS.checks("date-time", raises=(ValueError, TypeError))
def valid_datetime(value):
    if not isinstance(value, str):
        return True  # JSON Schema's type keyword owns non-string values.
    return "T" in value and datetime.fromisoformat(value.replace("Z", "+00:00")).tzinfo is not None


@FORMATS.checks("uri", raises=(ValueError, TypeError))
def valid_uri(value):
    if not isinstance(value, str):
        return True
    parsed = urlsplit(value)
    return parsed.scheme in {"https", "http"} and bool(parsed.netloc) and not any(
        char.isspace() for char in value)


def load_schemas(root: Path) -> dict[str, dict]:
    schemas = {}
    for name in SCHEMA_NAMES:
        try:
            schema = json.loads((root / "schemas" / f"{name}.schema.json").read_text(encoding="utf-8"))
            if schema.get("type") != "object" or not schema.get("required"):
                raise ValueError("Expected an object with required fields")
            _local_references_only(schema)
            Draft202012Validator.check_schema(schema)
            schemas[name] = schema
        except (OSError, ValueError, SchemaError) as exc:
            raise ValueError(f"INVALID_CONTRACT: {name}: {exc}") from exc
    return schemas


def validate_record(name: str, record: dict, schemas: dict[str, dict]) -> None:
    try:
        Draft202012Validator(schemas[name], format_checker=FORMATS).validate(record)
    except ValidationError as exc:
        location = ".".join(str(p) for p in exc.absolute_path) or "<root>"
        raise ValueError(f"INVALID_CONTRACT: {name}.{location}: {exc.message}") from exc
    if name == "github-code-source" and record["line_start"] is not None:
        if record["line_end"] is None or record["line_end"] < record["line_start"]:
            raise ValueError("INVALID_CONTRACT: invalid source line interval")
