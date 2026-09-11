"""Bounded local cache for public, commit-pinned GitHub responses only."""

import base64
import hashlib
import json
import os
import tempfile
import time
from pathlib import Path


class PublicResponseCache:
    max_bytes = 48 * 1024 * 1024
    max_entries = 128
    max_file_bytes = 12 * 1024 * 1024
    lifetime = 24 * 60 * 60

    def __init__(self, directory):
        self.directory = Path(directory) if directory else None

    def _path(self, key):
        return self.directory / (hashlib.sha256(key.encode("utf-8")).hexdigest() + ".json")

    def get(self, key):
        if not self.directory:
            return None
        try:
            path = self._path(key)
            if path.stat().st_size > self.max_file_bytes:
                return None
            value = json.loads(path.read_text(encoding="utf-8"))
            if value["key"] != key or not time.time() < value["expires"] <= time.time() + self.lifetime:
                return None
            body = base64.b64decode(value["body"], validate=True)
            if hashlib.sha256(body).hexdigest() != value["sha256"]:
                return None
            return body
        except (OSError, ValueError, KeyError, TypeError):
            return None

    def put(self, key, body):
        if not self.directory:
            return
        temporary = None
        try:
            self.directory.mkdir(parents=True, exist_ok=True)
            content = json.dumps({"key": key, "expires": time.time() + self.lifetime,
                                  "sha256": hashlib.sha256(body).hexdigest(),
                                  "body": base64.b64encode(body).decode("ascii")})
            if len(content) > self.max_file_bytes:
                return
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=self.directory,
                                             prefix=".response-", delete=False) as stream:
                temporary = Path(stream.name)
                stream.write(content)
            os.replace(temporary, self._path(key))
            entries = sorted((p for p in self.directory.glob("*.json") if not p.is_symlink()),
                             key=lambda p: p.stat().st_mtime, reverse=True)
            total = 0
            for index, path in enumerate(entries):
                total += path.stat().st_size
                if index >= self.max_entries or total > self.max_bytes:
                    path.unlink(missing_ok=True)
        except OSError:
            pass  # Cache availability never determines source validity.
        finally:
            if temporary:
                try:
                    temporary.unlink(missing_ok=True)
                except OSError:
                    pass
