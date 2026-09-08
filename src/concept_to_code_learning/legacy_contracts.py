"""Validate the four shared local JSON contracts."""

import json
from pathlib import Path

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError, ValidationError

SCHEMA_NAMES = ("concept", "code-mapping", "learning-artifact", "drift-finding")


def _local_references_only(value: object) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            if key in {"$ref", "$dynamicRef"} and (
                not isinstance(item, str) or not item.startswith("#")
            ):
                raise ValueError("INVALID_CONTRACT: remote schema references are not allowed")
            _local_references_only(item)
    elif isinstance(value, list):
        for item in value:
            _local_references_only(item)


def load_schemas(root: Path) -> dict[str, dict]:
    schemas = {}
    for name in SCHEMA_NAMES:
        path = root / "schemas" / "legacy" / f"{name}.schema.json"
        try:
            schema = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(schema, dict) or schema.get("type") != "object":
                raise ValueError("schema must define an object")
            if not schema.get("required") or not schema.get("properties"):
                raise ValueError("schema must define required fields and properties")
            _local_references_only(schema)
            Draft202012Validator.check_schema(schema)
        except (OSError, ValueError, SchemaError) as exc:
            raise ValueError(f"INVALID_CONTRACT: {path.name}: {exc}") from exc
        schemas[name] = schema
    return schemas


def validate_record(name: str, record: dict, schemas: dict[str, dict]) -> None:
    try:
        Draft202012Validator(schemas[name]).validate(record)
    except ValidationError as exc:
        location = ".".join(str(part) for part in exc.absolute_path) or "<root>"
        raise ValueError(f"INVALID_CONTRACT: {name}.{location}: {exc.message}") from exc
