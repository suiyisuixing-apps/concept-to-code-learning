import copy
import json
from pathlib import Path

import pytest

from concept_to_code_learning.legacy_contracts import SCHEMA_NAMES, load_schemas, validate_record
from concept_to_code_learning.scaffold import ast_location

ROOT = Path(__file__).resolve().parents[1]
SCHEMAS = load_schemas(ROOT)


def samples():
    concept = json.loads((ROOT / "demo/training-materials/concept.json").read_text())
    code = ast_location(ROOT, "demo/mini-fastapi-repo/app.py", "can_view_profile")
    return {
        "concept": concept,
        "code-mapping": {
            "concept_id": concept["concept_id"], "repository_commit": None,
            "code_locations": [code], "related_tests": [], "mapping_reason": "Fixture policy",
            "verification_status": "VERIFIED", "evidence": ["UNCOMMITTED_FIXTURE"],
        },
        "learning-artifact": {
            "concept_id": concept["concept_id"], "lesson_path": "reports/demo/guided-lesson.md",
            "runnable_example_path": "demo/mini-fastapi-repo/example.py",
            "practice_task_path": None, "grader_path": None, "status": "SCAFFOLD_DEMO",
            "evidence": ["Fixture schema example; not an execution assertion."],
        },
        "drift-finding": {
            "finding_id": "schema-only-drift-case", "concept_id": concept["concept_id"],
            "document_claim": "Hypothetical differing policy; contract test only.",
            "code_observation": "Active-user access gate.",
            "document_source": concept["source_locations"][0], "code_source": code,
            "status": "NEEDS_CONFIRMATION", "recommended_owner": "role:documents-model",
            "resolution": None,
        },
    }


@pytest.mark.parametrize("name", SCHEMA_NAMES)
def test_valid_records(name):
    validate_record(name, samples()[name], SCHEMAS)


@pytest.mark.parametrize("name,field", [
    (name, field) for name in SCHEMA_NAMES for field in SCHEMAS[name]["required"]
])
def test_every_required_field_is_enforced(name, field):
    record = samples()[name]
    del record[field]
    with pytest.raises(ValueError, match="INVALID_CONTRACT"):
        validate_record(name, record, SCHEMAS)


@pytest.mark.parametrize("name,field", [
    ("concept", "extraction_status"), ("code-mapping", "verification_status"),
    ("learning-artifact", "status"), ("drift-finding", "status"),
])
def test_free_text_cannot_masquerade_as_status(name, field):
    record = samples()[name]
    record[field] = "probably verified"
    with pytest.raises(ValueError, match="INVALID_CONTRACT"):
        validate_record(name, record, SCHEMAS)


@pytest.mark.parametrize("kind,key,value", [
    ("PPTX", "slide", 1), ("PDF", "page", 2), ("DOCX", "paragraph", 1),
    ("MARKDOWN_FIXTURE", "paragraph", 1),
])
def test_citations_require_format_specific_locations(kind, key, value):
    record = samples()["concept"]
    location = record["source_locations"][0]
    location["source_type"] = kind
    location[key] = value
    validate_record("concept", record, SCHEMAS)
    location[key] = None
    with pytest.raises(ValueError, match="INVALID_CONTRACT"):
        validate_record("concept", record, SCHEMAS)


@pytest.mark.parametrize("field", ["exists", "ast_verified"])
def test_verified_python_mapping_requires_actual_checks(field):
    record = samples()["code-mapping"]
    record["code_locations"][0][field] = False
    with pytest.raises(ValueError, match="INVALID_CONTRACT"):
        validate_record("code-mapping", record, SCHEMAS)


@pytest.mark.parametrize("field", ["runnable_example_path", "practice_task_path", "grader_path"])
def test_graded_artifact_requires_concrete_paths(field):
    record = samples()["learning-artifact"]
    record.update(status="GRADED_PASS", practice_task_path="practice/task.md",
                  grader_path="evals/graders/test_task.py")
    record[field] = None
    with pytest.raises(ValueError, match="INVALID_CONTRACT"):
        validate_record("learning-artifact", record, SCHEMAS)


def test_resolved_drift_requires_resolution():
    record = samples()["drift-finding"]
    record["status"] = "RESOLVED"
    with pytest.raises(ValueError, match="INVALID_CONTRACT"):
        validate_record("drift-finding", record, SCHEMAS)


def test_remote_schema_references_are_rejected_before_validation(project):
    schema = copy.deepcopy(SCHEMAS["concept"])
    schema["$ref"] = "https://example.invalid/never-fetch.json"
    (project / "schemas/legacy/concept.schema.json").write_text(json.dumps(schema))
    with pytest.raises(ValueError, match="remote schema references"):
        load_schemas(project)
