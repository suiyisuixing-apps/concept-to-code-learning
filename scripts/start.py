"""One-command local software entry after dependency installation and web build."""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

if __name__ == "__main__":
    from concept_to_code_learning.cli import main
    os.chdir(ROOT)
    raise SystemExit(main(["start", *sys.argv[1:]]))
