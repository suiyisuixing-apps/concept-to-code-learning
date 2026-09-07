import json
import subprocess
import sys

from concept_to_code.scaffold import ast_location, sha256


def cli(project, command):
    return subprocess.run([sys.executable, "scripts/tutor.py", command], cwd=project,
                          capture_output=True, text=True, timeout=45, check=False)


def test_doctor_reports_four_valid_schemas(project):
    result = cli(project, "doctor")
    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert report["schema_count"] == 4
    assert report["errors"] == []


def test_demo_runs_real_example_and_test_without_changing_inputs(project):
    paths = [p for p in (project / "demo").rglob("*") if p.is_file()]
    before = {str(p): sha256(p) for p in paths}
    result = cli(project, "demo")
    assert result.returncode == 0, result.stderr
    output = project / "reports/demo"
    mapping = json.loads((output / "concept-code-map.json").read_text())
    evidence = json.loads((output / "learning-evidence.json").read_text())
    for report in (mapping, evidence, json.loads(result.stdout)):
        assert report["mode"] == "FIXTURE"
        assert report["status"] == "SCAFFOLD_DEMO"
    assert (output / "guided-lesson.md").read_text().startswith(
        "---\nmode: FIXTURE\nstatus: SCAFFOLD_DEMO\n---"
    )
    assert mapping["mappings"][0]["code_locations"][0] == ast_location(
        project, "demo/mini-fastapi-repo/app.py", "can_view_profile"
    )
    assert evidence["example_run"]["exit_code"] == 0
    assert evidence["example_run"]["stdout"].strip() == "active=True inactive=False"
    assert evidence["test_run"]["exit_code"] == 0
    assert "1 passed" in evidence["test_run"]["stdout"]
    assert evidence["artifacts"][0]["practice_task_path"] is None
    assert {str(p): sha256(p) for p in paths} == before


def test_failed_execution_removes_previous_success_report(project):
    assert cli(project, "demo").returncode == 0
    app = project / "demo/mini-fastapi-repo/app.py"
    app.write_text(app.read_text().replace("return is_active", "return True"))
    result = cli(project, "demo")
    assert result.returncode == 1
    assert "EXECUTION_FAILED" in result.stderr
    assert not (project / "reports/demo").exists()


def test_changed_document_cannot_reuse_old_quote_hash(project):
    source = project / "demo/training-materials/onboarding.md"
    source.write_text(source.read_text().replace("Only an active", "Any"))
    result = cli(project, "demo")
    assert result.returncode == 1
    assert "NEEDS_CONFIRMATION" in result.stderr
    assert not (project / "reports/demo").exists()


def test_nonexistent_symbol_is_not_verified(project):
    app = project / "demo/mini-fastapi-repo/app.py"
    app.write_text(app.read_text().replace("can_view_profile", "different_function"))
    result = cli(project, "demo")
    assert result.returncode == 1
    assert "expected one top-level function" in result.stderr


def test_unknown_command_exits_two(project):
    result = cli(project, "parse-pdf")
    assert result.returncode == 2
    assert "invalid choice" in result.stderr
