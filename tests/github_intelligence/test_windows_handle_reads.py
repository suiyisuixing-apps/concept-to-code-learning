"""Native Windows races; skipped elsewhere, required by the Windows CI job."""

import os
import subprocess

import pytest

from concept_to_code_learning.github_intelligence.errors import SourceError
from concept_to_code_learning.github_intelligence.registry import LocalRegistry

pytestmark = pytest.mark.skipif(os.name != "nt", reason="Native Windows filesystem boundary")


def junction(path, target):
    subprocess.run(["cmd", "/c", "mklink", "/J", str(path), str(target)],
                   check=True, capture_output=True)


def test_directory_junction_swap_cannot_select_outside_bytes(tmp_path, monkeypatch):
    from concept_to_code_learning.github_intelligence import windows_files

    root, outside = tmp_path / "中文 授权目录", tmp_path / "outside"
    sub = root / "源码 文件夹"
    sub.mkdir(parents=True)
    outside.mkdir()
    (sub / "model.py").write_bytes(b"authorized source")
    (outside / "model.py").write_bytes(b"OUTSIDE SECRET MUST NOT BE READ")
    registry = LocalRegistry((root,))
    handle = registry.handles()[0]
    assert registry.read(handle, "源码 文件夹/model.py") == b"authorized source"
    original_open = windows_files._open_child
    retired = root / "original-directory"
    raced = []

    def race(parent_fd, name, directory):
        if name != "model.py":
            return original_open(parent_fd, name, directory)
        sub.rename(retired)
        junction(sub, outside)
        raced.append(True)
        return original_open(parent_fd, name, directory)

    monkeypatch.setattr(windows_files, "_open_child", race)
    try:
        # Read while the pathname points outside. Only the held parent identifies
        # the authorized directory. Windows prevents renaming that parent back
        # while its child file is open, so restore after the owned handles close.
        assert registry.read(handle, "源码 文件夹/model.py") == b"authorized source"
    finally:
        if retired.exists():
            if sub.exists():
                os.rmdir(sub)
            retired.rename(sub)
    assert raced == [True]
    assert (sub / "model.py").read_bytes() == b"authorized source"


def test_root_identity_checked_on_actual_open_handle_after_aba(tmp_path, monkeypatch):
    from concept_to_code_learning.github_intelligence import windows_files

    root = tmp_path / "root"
    root.mkdir()
    (root / "main.py").write_bytes(b"original")
    registry = LocalRegistry((root,))
    handle = registry.handles()[0]
    original_open = windows_files._open_root
    retired, outside = tmp_path / "original", tmp_path / "outside"
    outside.mkdir()
    (outside / "main.py").write_bytes(b"replacement")
    raced = []

    def replacement(path):
        root.rename(retired)
        outside.rename(root)
        fd = None
        try:
            fd = original_open(path)
            root.rename(outside)
            retired.rename(root)
            raced.append(True)
            return fd
        except BaseException:
            if fd is not None:
                os.close(fd)
            raise

    monkeypatch.setattr(windows_files, "_open_root", replacement)
    with pytest.raises(SourceError, match="AUTH_REQUIRED"):
        registry.read(handle, "main.py")
    assert raced == [True]
    assert (root / "main.py").read_bytes() == b"original"


def test_junction_and_alternate_stream_are_rejected(tmp_path):
    root, outside = tmp_path / "root", tmp_path / "outside"
    root.mkdir()
    outside.mkdir()
    (outside / "main.py").write_bytes(b"outside")
    junction(root / "link", outside)
    registry = LocalRegistry((root,))
    handle = registry.handles()[0]
    for path in ("link/main.py", "main.py:stream", "."):
        with pytest.raises(SourceError, match="AUTH_REQUIRED"):
            registry.read(handle, path)


def test_regular_file_and_size_limit_use_opened_descriptor(tmp_path):
    (tmp_path / "main.py").write_bytes(b"x" * (1024 * 1024 + 1))
    registry = LocalRegistry((tmp_path,))
    with pytest.raises(SourceError, match="FILE_NOT_FOUND"):
        registry.read(registry.handles()[0], "main.py")
