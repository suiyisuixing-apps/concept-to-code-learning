"""Local registry tests: authorized handles, escape rejection."""

from __future__ import annotations

from pathlib import Path

from concept_to_code_learning.github_intelligence.registry import LocalRegistry


class TestLocalRegistryHandles:
    def test_returns_opaque_authorized_handles(self, authorized_local_root: Path):
        registry = LocalRegistry((authorized_local_root,))
        handles = registry.handles()
        assert len(handles) == 1
        assert handles[0].startswith("local-")
        assert str(authorized_local_root) not in handles[0]

    def test_no_roots_returns_empty(self):
        registry = LocalRegistry(())
        assert registry.handles() == []

    def test_is_authorized_for_known_handle(self, authorized_local_root: Path):
        registry = LocalRegistry((authorized_local_root,))
        assert registry.is_authorized(registry.handles()[0])

    def test_is_authorized_rejects_unknown_handle(self, authorized_local_root: Path):
        registry = LocalRegistry((authorized_local_root,))
        assert not registry.is_authorized("/etc/passwd")

    def test_root_for_returns_path_for_known(self, authorized_local_root: Path):
        registry = LocalRegistry((authorized_local_root,))
        result = registry.root_for(registry.handles()[0])
        assert result == authorized_local_root.resolve()

    def test_root_for_returns_none_for_unknown(self, authorized_local_root: Path):
        registry = LocalRegistry((authorized_local_root,))
        assert registry.root_for("/unknown") is None


class TestLocalRegistryEscape:
    def test_rejects_unknown_handle(self, authorized_local_root: Path):
        registry = LocalRegistry((authorized_local_root,))
        assert registry.rejects_escape("/unknown", "README.md") is True

    def test_allows_path_inside_root(self, authorized_local_root: Path):
        registry = LocalRegistry((authorized_local_root,))
        assert registry.rejects_escape(
            registry.handles()[0], "README.md") is False

    def test_rejects_path_escape_via_dotdot(self, authorized_local_root: Path):
        registry = LocalRegistry((authorized_local_root,))
        handle = registry.handles()[0]
        assert registry.rejects_escape(handle, "../../etc/passwd") is True

    def test_rejects_absolute_path(self, authorized_local_root: Path):
        registry = LocalRegistry((authorized_local_root,))
        handle = registry.handles()[0]
        assert registry.rejects_escape(handle, "/etc/passwd") is True
