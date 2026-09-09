"""Package only the portable Skill entrypoint, client and its API reference."""

import argparse
import hashlib
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILES = {"SKILL.md": "SKILL.md", "scripts/learning_client.py": "scripts/learning_client.py",
         "references/full-learning-api.md": "references/full-learning-api.md"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "dist/skills/concept-to-code-learning.zip")
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.output.is_symlink():
        parser.error("Output must not be a symlink")
    hashes = {}
    with zipfile.ZipFile(args.output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for source, target in FILES.items():
            raw = (ROOT / source).read_bytes()
            hashes[target] = hashlib.sha256(raw).hexdigest()
            info = zipfile.ZipInfo("concept-to-code-learning/" + target, date_time=(2026, 9, 9, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, raw)
    print(json.dumps({"package": str(args.output), "files": hashes,
                      "sha256": hashlib.sha256(args.output.read_bytes()).hexdigest()}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
