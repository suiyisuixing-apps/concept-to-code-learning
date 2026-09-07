import json
from pathlib import Path

import pytest
import yaml

from concept_to_code_learning.scaffold import doctor, safe_file

ROOT = Path(__file__).resolve().parents[1]


def test_required_checkout_structure():
    assert doctor(ROOT)["errors"] == []


def test_skill_frontmatter_is_valid_yaml():
    raw = (ROOT / "SKILL.md").read_text().split("---", 2)[1]
    metadata = yaml.safe_load(raw)
    assert metadata["name"] == "concept-to-code-learning"
    assert isinstance(metadata["description"], str) and metadata["description"].strip()


def test_ci_cost_and_permission_constraints():
    workflow = yaml.load((ROOT / ".github/workflows/ci.yml").read_text(), Loader=yaml.BaseLoader)
    assert set(workflow["on"]) == {"push", "pull_request"}
    assert all(trigger["branches"] == ["main"] for trigger in workflow["on"].values())
    assert workflow["permissions"] == {"contents": "read"}
    assert workflow["concurrency"]["cancel-in-progress"] == "true"
    assert "github.head_ref" in workflow["concurrency"]["group"]
    assert len(workflow["jobs"]) == 1
    job = workflow["jobs"]["phase0-checks"]
    assert int(job["timeout-minutes"]) <= 10
    assert job["runs-on"] == "ubuntu-latest"
    assert "strategy" not in job
    assert [step["run"] for step in job["steps"] if "run" in step] == [
        'python -m pip install -e ".[dev]"', "ruff check .", "pytest -q",
        "python scripts/tutor.py doctor", "python scripts/tutor.py demo",
        "npm ci", "npm test", "npm run build",
    ]


@pytest.mark.parametrize("missing", ["SKILL.md", "references/document-grounding.md",
                                     "src/concept_to_code_learning/runtime/__init__.py"])
def test_doctor_fails_when_required_file_is_missing(project, missing):
    (project / missing).unlink()
    result = doctor(project)
    assert result["status"] == "FAILED"
    assert any(missing in error for error in result["errors"])


def test_doctor_rejects_malformed_schema(project):
    (project / "schemas/legacy/concept.schema.json").write_text("{broken")
    result = doctor(project)
    assert result["status"] == "FAILED"
    assert any("INVALID_CONTRACT" in error for error in result["errors"])


def test_doctor_rejects_semantically_invalid_schema(project):
    path = project / "schemas/legacy/concept.schema.json"
    schema = json.loads(path.read_text())
    schema["properties"]["confidence"]["type"] = "invented-type"
    path.write_text(json.dumps(schema))
    assert doctor(project)["status"] == "FAILED"


def test_mapping_paths_cannot_escape_checkout(project):
    outside = project.parent / "outside.py"
    outside.write_text("value = 1\n")
    with pytest.raises(ValueError, match="out-of-root"):
        safe_file(project, "../outside.py")
