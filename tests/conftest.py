import shutil
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def project(tmp_path):
    target = tmp_path / "checkout"
    shutil.copytree(ROOT, target, ignore=shutil.ignore_patterns(
        ".git", ".venv", "node_modules", "dist", "data", "artifacts", ".impeccable", "__pycache__", ".pytest_cache", ".ruff_cache", "*.egg-info"
    ))
    return target
