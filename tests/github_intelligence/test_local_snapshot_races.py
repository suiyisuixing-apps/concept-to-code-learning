"""Local evidence stays bound while an authorized repository changes."""

import asyncio
import os
import subprocess

import pytest

from concept_to_code_learning.full_contracts import models as m
from concept_to_code_learning.github_intelligence import local
from concept_to_code_learning.github_intelligence.errors import SourceError
from concept_to_code_learning.github_intelligence.registry import LocalRegistry

from .conftest import FROZEN_LICENSE_TEXT


def test_replaced_root_revokes_handle_and_read(tmp_path):
    root = tmp_path / "authorized"
    root.mkdir()
    (root / "main.py").write_bytes(b"original")
    registry = LocalRegistry((root,))
    handle = registry.handles()[0]
    assert registry.read(handle, "main.py") == b"original"
    root.rename(tmp_path / "retired")
    root.mkdir()
    (root / "main.py").write_bytes(b"replacement")
    # A retained path string does not authorize a different directory identity.
    with pytest.raises(SourceError, match="AUTH_REQUIRED"):
        registry.read(handle, "main.py")
    assert not registry.is_authorized(handle)
    assert registry.root_for(handle) is None


@pytest.mark.skipif(os.name == "nt", reason="Windows uses native handle-relative opens")
def test_unsupported_platform_does_not_fall_back_to_unsafe_path_open(tmp_path, monkeypatch):
    (tmp_path / "main.py").write_bytes(b"original")
    registry = LocalRegistry((tmp_path,))
    monkeypatch.setattr(os, "supports_dir_fd", set())
    with pytest.raises(SourceError, match="AUTH_REQUIRED"):
        registry.read(registry.handles()[0], "main.py")


@pytest.mark.parametrize("advance_head", [False, True])
def test_local_evidence_compares_bytes_to_recorded_commit(tmp_path, monkeypatch, advance_head):
    root = tmp_path / "repo"
    root.mkdir()

    def git(*args):
        return subprocess.run(
            ["git", "-C", str(root), "-c", "user.name=Test", "-c",
             "user.email=test@example.invalid", "-c", "commit.gpgsign=false", *args],
            check=True, capture_output=True,
        ).stdout

    git("init")
    git("config", "core.autocrlf", "false")
    (root / "LICENSE").write_text(FROZEN_LICENSE_TEXT, encoding="utf-8")
    source_a = b"def dependency(value):\n    return value + 1\n"
    source_b = b"def dependency(value):\n    return value + 2\n"
    (root / "main.py").write_bytes(source_a)
    git("add", ".")
    git("commit", "-m", "first synthetic revision")
    commit_a = git("rev-parse", "HEAD").decode().strip()
    (root / "main.py").write_bytes(source_b)
    git("add", ".")
    git("commit", "-m", "second synthetic revision")
    commit_b = git("rev-parse", "HEAD").decode().strip()
    git("update-ref", "HEAD", commit_a)
    registry = LocalRegistry((root,))
    provider = local.LocalSources(registry)
    query = m.SourceQuery(
        mode="LIVE", query_id=m.uid(), question="dependency", concept_terms=["dependency"],
        source_mode="local_authorized", local_handle=registry.handles()[0], status="AUTHORIZED",
    )
    real_git = local.git

    async def changing_git(root, *args, **kwargs):
        value = await real_git(root, *args, **kwargs)
        if advance_head and args[:1] == ("rev-parse",):
            git("update-ref", "HEAD", commit_b)
        return value

    monkeypatch.setattr(local, "git", changing_git)

    async def scenario():
        found = await provider.search(query)
        receipt = await provider.verify(query, found.candidates[0], "a" * 64)
        evidence = receipt.evidence
        assert evidence.commit_sha == commit_a
        assert git("show", evidence.commit_sha + ":main.py") == source_a
        assert evidence.file_sha256 == m.digest(source_b.decode())
        assert evidence.dirty  # The supplied bytes are from B, while the recorded version is A.
        assert "value + 2" in evidence.code_excerpt

    asyncio.run(scenario())
