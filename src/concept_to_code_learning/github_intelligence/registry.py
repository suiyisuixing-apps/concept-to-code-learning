"""Local handle registry. Host-configured; no web path endpoint.

Per INTERFACES.md, local_authorized handles are configured outside HTTP by
the host process member module. This registry only ever returns handles that
were explicitly authorized at construction time; it never accepts arbitrary
paths supplied by a request.
"""

from __future__ import annotations

from pathlib import Path


class LocalRegistry:
    """Read-only registry of host-authorized local repository roots."""

    def __init__(self, authorized_roots: tuple[Path, ...]):
        # Roots are resolved to absolute paths at construction; later lookups
        # compare canonical strings so symlinked duplicates collapse.
        self._roots = tuple(self._canonical(root) for root in authorized_roots)

    @staticmethod
    def _canonical(root: Path) -> Path:
        # resolve(strict=True) is enforced in ProviderSettings.from_env; the
        # registry only normalizes for comparison, it does not re-validate.
        return root.resolve() if root.exists() else root

    def handles(self) -> list[str]:
        """Return the string identifiers of authorized local roots."""
        return [str(root) for root in self._roots]

    def is_authorized(self, handle: str) -> bool:
        return handle in self.handles()

    def root_for(self, handle: str) -> Path | None:
        for root in self._roots:
            if str(root) == handle:
                return root
        return None

    def rejects_escape(self, handle: str, requested_path: str) -> bool:
        """Return True when requested_path would escape the registered root.

        Local reads must stay inside the Git root and must not follow symlinks
        that point outside. This guard is called before any file is opened.
        """
        root = self.root_for(handle)
        if root is None:
            return True
        candidate = (root / requested_path).resolve()
        try:
            candidate.relative_to(root.resolve())
        except ValueError:
            return True
        # Reject if the resolved path is a symlink whose target leaves the root.
        if candidate.is_symlink():
            target = candidate.resolve()
            try:
                target.relative_to(root.resolve())
            except ValueError:
                return True
        return False
