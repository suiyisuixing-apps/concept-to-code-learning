"""Only fixed synthetic fixtures are supported; this is not a general pipeline."""

import ast
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from concept_to_code.contracts import load_schemas, validate_record

REQUIRED_DIRS = (
    "scripts", "src/concept_to_code", "schemas", "references", "evals",
    "evals/concept-cases", "evals/mapping-cases", "evals/exercise-cases", "evals/graders",
    "demo/training-materials", "demo/mini-fastapi-repo", "demo/expected-results",
    "tests", "reports", "docs", ".github/workflows", ".github/ISSUE_TEMPLATE",
)
MODULES = ("documents", "code_intel", "teaching", "execution", "runtime", "reporting")
REFERENCES = (
    "document-grounding", "code-mapping-policy", "runnable-example-policy",
    "exercise-grading-policy", "documentation-drift-policy",
)
DOCS = (
    "product-scope", "non-goals", "architecture", "data-contracts", "roles-and-ownership",
    "roadmap", "competition-assumptions", "competition-provenance", "reuse-ledger",
    "competitor-boundary", "decision-log", "demo-story",
)
REQUIRED_FILES = (
    "SKILL.md", "README.md", "CONTRIBUTING.md", "SECURITY.md", "CODEOWNERS",
    "pyproject.toml", ".gitignore", ".env.example", "scripts/tutor.py",
    "src/concept_to_code/__init__.py", "src/concept_to_code/cli.py",
    "src/concept_to_code/contracts.py", "src/concept_to_code/scaffold.py",
    "evals/README.md", "demo/README.md", "demo/training-materials/README.md",
    "demo/mini-fastapi-repo/README.md", "demo/expected-results/README.md", "reports/README.md",
    "tests/test_cli.py", "tests/test_contracts.py", "tests/test_repository_structure.py",
    ".github/workflows/ci.yml", ".github/ISSUE_TEMPLATE/feature.yml",
    ".github/ISSUE_TEMPLATE/bug.yml", ".github/ISSUE_TEMPLATE/research.yml",
    ".github/pull_request_template.md",
    *(f"references/{name}.md" for name in REFERENCES),
    *(f"docs/{name}.md" for name in DOCS),
    *(f"src/concept_to_code/{name}/__init__.py" for name in MODULES),
)


def doctor(root: Path) -> dict:
    errors = []
    if sys.version_info[:2] != (3, 12):
        errors.append("Python 3.12 is required")
    errors.extend(f"Missing directory: {p}" for p in REQUIRED_DIRS if not (root / p).is_dir())
    errors.extend(f"Missing file: {p}" for p in REQUIRED_FILES if not (root / p).is_file())
    try:
        schemas = load_schemas(root)
    except ValueError as exc:
        errors.append(str(exc))
        schemas = {}
    return {
        "status": "FAILED" if errors else "DONE",
        "python": sys.version.split()[0], "schema_count": len(schemas),
        "required_files_checked": len(REQUIRED_FILES), "errors": errors,
    }


def safe_file(root: Path, relative: str) -> Path:
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()) or not path.is_file():
        raise ValueError(f"NEEDS_CONFIRMATION: missing or out-of-root file: {relative}")
    return path


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def ast_location(root: Path, relative: str, symbol: str, *, is_test: bool = False) -> dict:
    path = safe_file(root, relative)
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except SyntaxError as exc:
        raise ValueError(f"NEEDS_CONFIRMATION: invalid Python: {relative}") from exc
    matches = [node for node in tree.body if isinstance(node, ast.FunctionDef)
               and node.name == symbol]
    if len(matches) != 1:
        raise ValueError(f"NEEDS_CONFIRMATION: expected one top-level function: {symbol}")
    node = matches[0]
    return {
        "file": relative, "symbol": symbol, "symbol_type": "test" if is_test else "function",
        "line_start": node.lineno, "line_end": node.end_lineno,
        "exists": True, "ast_verified": True,
    }


def repository_identity(root: Path) -> dict:
    def git(*args: str) -> str | None:
        try:
            result = subprocess.run(["git", "-C", str(root), *args], capture_output=True,
                                    text=True, timeout=5, check=False)
        except (OSError, subprocess.TimeoutExpired):
            return None
        return result.stdout.strip() if result.returncode == 0 else None

    top = git("rev-parse", "--show-toplevel")
    commit = git("rev-parse", "HEAD") if top and Path(top).resolve() == root.resolve() else None
    return {
        "repository_commit": commit,
        "snapshot_status": "COMMIT_AND_FILE_HASHES" if commit else "UNCOMMITTED_FIXTURE",
        "worktree_dirty": bool(git("status", "--porcelain")) if commit else True,
    }


def _execute(workspace: Path, arguments: list[str], expected: str | None = None) -> dict:
    env = {
        "PATH": os.defpath, "HOME": str(workspace), "LC_ALL": "C",
        "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1", "PYTHONDONTWRITEBYTECODE": "1",
    }
    try:
        result = subprocess.run([sys.executable, *arguments], cwd=workspace, env=env,
                                text=True, capture_output=True, timeout=30, check=False)
    except subprocess.TimeoutExpired as exc:
        raise ValueError("EXECUTION_FAILED: fixture command exceeded 30 seconds") from exc
    expected_matches = expected is None or result.stdout.strip() == expected
    if result.returncode != 0 or not expected_matches:
        raise ValueError(
            f"EXECUTION_FAILED: {' '.join(arguments)}; exit={result.returncode}; "
            f"expected_matches={expected_matches}; {result.stdout[-1500:]}{result.stderr[-1500:]}"
        )
    return {"command": ["python", *arguments], "exit_code": result.returncode,
            "stdout": result.stdout, "stderr": result.stderr,
            "expected_output_matched": expected_matches, "timeout_seconds": 30}


def run_demo(root: Path) -> dict:
    root = root.resolve()
    reports = root / "reports"
    if reports.is_symlink() or not reports.is_dir():
        raise ValueError("MISSING_INPUT: a local reports directory is required")
    output = reports / "demo"
    if output.is_symlink():
        raise ValueError("NEEDS_CONFIRMATION: reports/demo must not be a symlink")
    if output.exists():
        shutil.rmtree(output)
    diagnosis = doctor(root)
    if diagnosis["status"] != "DONE":
        raise ValueError("MISSING_INPUT: " + "; ".join(diagnosis["errors"]))
    schemas = load_schemas(root)
    concept_path = safe_file(root, "demo/training-materials/concept.json")
    concept = json.loads(concept_path.read_text(encoding="utf-8"))
    validate_record("concept", concept, schemas)
    source = concept["source_locations"][0]
    material = safe_file(root, source["file"])
    parts = material.read_text(encoding="utf-8").strip().split("\n\n")
    if len(parts) != 2 or parts[0] != f"# {source['section']}" or source["paragraph"] != 1:
        raise ValueError("NEEDS_CONFIRMATION: fixture section/paragraph does not match")
    if hashlib.sha256(parts[1].encode("utf-8")).hexdigest() != source["quote_hash"]:
        raise ValueError("NEEDS_CONFIRMATION: source quote hash does not match")
    code = ast_location(root, "demo/mini-fastapi-repo/app.py", "can_view_profile")
    test = ast_location(root, "demo/mini-fastapi-repo/tests/test_app.py",
                        "test_profile_requires_active_user", is_test=True)
    identity = repository_identity(root)
    inputs = [source["file"], "demo/training-materials/concept.json", code["file"],
              test["file"], "demo/mini-fastapi-repo/example.py"]
    hashes = {name: sha256(safe_file(root, name)) for name in inputs}
    with tempfile.TemporaryDirectory(prefix="concept-to-code-fixture-") as temp:
        workspace = Path(temp)
        (workspace / "tests").mkdir()
        for name in ("app.py", "example.py", "tests/test_app.py"):
            shutil.copyfile(safe_file(root, f"demo/mini-fastapi-repo/{name}"), workspace / name)
        example_run = _execute(workspace, ["example.py"], "active=True inactive=False")
        test_run = _execute(workspace, ["-m", "pytest", "-q", "-p", "no:cacheprovider",
                                        "tests/test_app.py"])
    mapping = {
        "concept_id": concept["concept_id"], "repository_commit": identity["repository_commit"],
        "code_locations": [code], "related_tests": [test],
        "mapping_reason": "Predefined synthetic access-policy concept maps to its reviewed helper.",
        "verification_status": "VERIFIED",
        "evidence": ["Filesystem and Python AST verified both locations.",
                     f"Snapshot: {identity['snapshot_status']}",
                     f"Function file SHA-256: {hashes[code['file']]}",
                     "Semantic link is predefined fixture data; no intelligent mapping was run."],
    }
    artifact = {
        "concept_id": concept["concept_id"], "lesson_path": "reports/demo/guided-lesson.md",
        "runnable_example_path": "demo/mini-fastapi-repo/example.py",
        "practice_task_path": None, "grader_path": None, "status": "SCAFFOLD_DEMO",
        "evidence": ["Synthetic example exited 0 with expected output.",
                     "Synthetic pytest exited 0. No learner exercise was graded."],
    }
    validate_record("code-mapping", mapping, schemas)
    validate_record("learning-artifact", artifact, schemas)
    envelope = {"mode": "FIXTURE", "status": "SCAFFOLD_DEMO"}
    map_report = {**envelope, "concepts": [concept], "mappings": [mapping]}
    evidence = {
        **envelope, "repository": identity, "input_sha256": hashes,
        "python": sys.version.split()[0], "artifacts": [artifact],
        "example_run": example_run, "test_run": test_run,
        "execution_scope": "Reviewed synthetic files copied into a temporary directory.",
        "limitations": ["No Office/PDF extraction or model inference.",
                        "No generated learner exercise, grading pipeline, or drift detection.",
                        "A temporary directory is not an untrusted-code security sandbox."],
    }
    lesson = (
        "---\nmode: FIXTURE\nstatus: SCAFFOLD_DEMO\n---\n\n"
        f"# {concept['name']}\n\n{concept['learning_objective']}\n\n"
        f"Source: `{source['file']}`, section **{source['section']}**, paragraph 1.\n\n"
        f"> {parts[1]}\n\n"
        f"Implementation: `{code['file']}:{code['line_start']}-{code['line_end']}`, "
        f"`{code['symbol']}`. The helper returns the Boolean `is_active` input; an active "
        "user is allowed and an inactive user is denied.\n\n"
        f"Test: `{test['file']}:{test['line_start']}-{test['line_end']}`, "
        f"`{test['symbol']}` checks both cases. The example and pytest actually ran "
        "in a temporary copy with exit code 0.\n\n"
        "This is a predefined fixture demonstration. It is not full Office/PDF parsing, "
        "a FastAPI server, a generated/graded exercise, or drift detection.\n"
    )
    with tempfile.TemporaryDirectory(prefix=".demo-", dir=reports) as temp:
        staged = Path(temp) / "demo"
        staged.mkdir()
        for name, value in (("concept-code-map.json", map_report),
                            ("learning-evidence.json", evidence)):
            (staged / name).write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n",
                                      encoding="utf-8")
        (staged / "guided-lesson.md").write_text(lesson, encoding="utf-8")
        staged.rename(output)
    return evidence
