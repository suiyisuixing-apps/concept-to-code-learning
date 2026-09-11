"""Disposable parser worker: bounded resources, no inherited credentials, no network."""

import base64
import json
import sys

from ..full_learning.errors import LearningError
from .full import MAX_UNITS, FullDocumentProvider, fail


def denied(*args, **kwargs):
    raise OSError("Parser network access is disabled")


def main():
    try:
        import resource

        resource.setrlimit(resource.RLIMIT_CPU, (25, 30))
        resource.setrlimit(resource.RLIMIT_AS, (2 * 1024**3, 2 * 1024**3))
    except (ImportError, ValueError, OSError):
        pass  # Windows still has the parent-enforced timeout and input/output caps.
    sys.addaudithook(lambda event, args: denied() if event.startswith("socket.") else None)
    try:
        content = sys.stdin.buffer.read(20 * 1024 * 1024 + 1)
        if len(content) > 20 * 1024 * 1024:
            raise fail("FILE_TOO_LARGE", "文件超过解析上限。", 413)
        provider = FullDocumentProvider.__new__(FullDocumentProvider)
        units, assets, warnings, capabilities = provider.parse(sys.argv[1], content, sys.argv[2])
        if len(units) > MAX_UNITS:
            raise fail("FILE_TOO_LARGE", "文档章节超过 300 个。", 413)
        value = {
            "units": [u.model_dump(mode="json") for u in units],
            "assets": {
                key: {
                    "content": base64.b64encode(a.content).decode("ascii"),
                    "media_type": a.media_type,
                    "file_name": a.file_name,
                }
                for key, a in assets.items()
            },
            "warnings": warnings,
            "capabilities": capabilities,
        }
    except LearningError as exc:
        value = {"error": exc.code, "message": exc.message, "status": exc.http_status}
    except Exception:
        value = {"error": "INVALID_FILE", "message": "文档损坏或无法安全解析。", "status": 422}
    sys.stdout.buffer.write(json.dumps(value, ensure_ascii=False).encode("utf-8"))


if __name__ == "__main__":
    main()
