"""Opaque handles for explicitly configured local roots. Paths never reach the browser."""

import hashlib
import os
import stat
from pathlib import Path, PurePosixPath

from .errors import SourceError


class LocalRegistry:
    def __init__(self, authorized_roots):
        self._roots = {}
        self._identities = {}
        for root in authorized_roots:
            root = Path(root).resolve(strict=True)
            if not root.is_dir():
                raise ValueError("Local root is not a directory")
            handle = "local-" + hashlib.sha256(os.fsencode(root)).hexdigest()[:24]
            self._roots[handle] = root
            info = root.stat()
            self._identities[handle] = (info.st_dev, info.st_ino)

    def handles(self):
        return [
            handle
            for handle, root in self._roots.items()
            if root.is_dir() and not root.is_symlink()
        ]

    def is_authorized(self, handle):
        return handle in self.handles()

    def root_for(self, handle):
        return self._roots.get(handle) if self.is_authorized(handle) else None

    def rejects_escape(self, handle, requested_path):
        root = self.root_for(handle)
        path = PurePosixPath(requested_path)
        if (
            root is None
            or not requested_path
            or path.is_absolute()
            or ".." in path.parts
            or "\\" in requested_path
            or "\x00" in requested_path
        ):
            return True
        current = root
        for part in path.parts:
            current = current / part
            if current.is_symlink():
                return True
        return not current.resolve().is_relative_to(root)

    def read(self, handle, path):
        if self.rejects_escape(handle, path):
            raise SourceError("AUTH_REQUIRED", "local", "源码路径超出授权范围或包含符号链接。", 403)
        target = self.root_for(handle) / path
        # O_NOFOLLOW defends the final component, repeated canonical check defends parents.
        parent_fds = []
        try:
            if os.open in os.supports_dir_fd:
                flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
                current = os.open(self.root_for(handle), flags)
                parent_fds.append(current)
                info = os.fstat(current)
                if (info.st_dev, info.st_ino) != self._identities[handle]:
                    raise SourceError("AUTH_REQUIRED", "local", "授权根目录已被替换。", 403)
                parts = PurePosixPath(path).parts
                for part in parts[:-1]:
                    current = os.open(part, flags, dir_fd=current)
                    parent_fds.append(current)
                fd = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW, dir_fd=current)
            else:
                fd = os.open(target, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
        finally:
            for parent_fd in reversed(parent_fds):
                os.close(parent_fd)
        try:
            info = os.fstat(fd)
            if not stat.S_ISREG(info.st_mode) or info.st_size > 1024 * 1024:
                raise SourceError(
                    "FILE_NOT_FOUND", "local", "仅支持不超过 1 MiB 的普通源码文件。", 422
                )
            if self.rejects_escape(handle, path):
                raise SourceError("AUTH_REQUIRED", "local", "本地路径在读取时发生变化。", 403)
            with os.fdopen(fd, "rb", closefd=False) as source:
                raw = source.read(1024 * 1024 + 1)
            if len(raw) > 1024 * 1024:
                raise SourceError("FILE_NOT_FOUND", "local", "文件超过读取上限。", 413)
            return raw
        finally:
            os.close(fd)
