import json
from pathlib import Path

import pytest
import yaml

from concept_to_code_learning.scaffold import doctor, safe_file

ROOT = Path(__file__).resolve().parents[1]


def test_required_checkout_structure():
    assert doctor(ROOT)["errors"] == []


def test_skill_frontmatter_is_valid_yaml():
    raw = (ROOT / "SKILL.md").read_text(encoding="utf-8").split("---", 2)[1]
    metadata = yaml.safe_load(raw)
    assert metadata["name"] == "concept-to-code-learning"
    assert isinstance(metadata["description"], str) and metadata["description"].strip()


def test_ci_cost_and_permission_constraints():
    workflow = yaml.load((ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8"), Loader=yaml.BaseLoader)
    assert set(workflow["on"]) == {"push", "pull_request"}
    assert workflow["on"]["push"]["branches"] == ["main"]
    # Windows fixes target the unmerged workspace PR; keep the same bounded checks.
    assert workflow["on"]["pull_request"]["branches"] == [
        "main", "feat/repository-learning-workspace",
    ]
    assert workflow["permissions"] == {"contents": "read"}
    assert workflow["concurrency"]["cancel-in-progress"] == "true"
    assert "github.head_ref" in workflow["concurrency"]["group"]
    # One required Linux check and at most one native Windows check, with no matrix fan-out.
    assert "phase0-checks" in workflow["jobs"] and len(workflow["jobs"]) <= 2
    assert workflow["jobs"]["phase0-checks"]["runs-on"] == "ubuntu-latest"
    for job in workflow["jobs"].values():
        assert int(job["timeout-minutes"]) <= 10
        assert job["runs-on"] in {"ubuntu-latest", "windows-latest"}
        assert "strategy" not in job
        assert "permissions" not in job
        commands = [step["run"] for step in job["steps"] if "run" in step]
        assert "pytest -q" in commands and "npm test" in commands and "npm run build" in commands
        for step in job["steps"]:
            if step.get("uses", "").startswith("actions/checkout@"):
                assert step["with"]["persist-credentials"] == "false"


@pytest.mark.parametrize("missing", ["SKILL.md", "references/document-grounding.md",
                                     "src/concept_to_code_learning/runtime/__init__.py"])
def test_doctor_fails_when_required_file_is_missing(project, missing):
    (project / missing).unlink()
    result = doctor(project)
    assert result["status"] == "FAILED"
    assert any(missing in error for error in result["errors"])


def test_doctor_rejects_malformed_schema(project):
    (project / "schemas/legacy/concept.schema.json").write_text("{broken", encoding="utf-8")
    result = doctor(project)
    assert result["status"] == "FAILED"
    assert any("INVALID_CONTRACT" in error for error in result["errors"])


def test_doctor_rejects_semantically_invalid_schema(project):
    path = project / "schemas/legacy/concept.schema.json"
    schema = json.loads(path.read_text(encoding="utf-8"))
    schema["properties"]["confidence"]["type"] = "invented-type"
    path.write_text(json.dumps(schema), encoding="utf-8")
    assert doctor(project)["status"] == "FAILED"


def test_mapping_paths_cannot_escape_checkout(project):
    outside = project.parent / "outside.py"
    outside.write_text("value = 1\n", encoding="utf-8")
    with pytest.raises(ValueError, match="out-of-root"):
        safe_file(project, "../outside.py")
