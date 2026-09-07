"""Small checkout-oriented command line entry point."""

import argparse
import json
import sys
from pathlib import Path

from concept_to_code.scaffold import doctor, run_demo


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Concept-to-Code Phase 0 fixture scaffold")
    parser.add_argument("command", choices=("doctor", "demo"))
    args = parser.parse_args(argv)
    root = Path.cwd().resolve()
    if args.command == "doctor":
        result = doctor(root)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["status"] == "DONE" else 1
    try:
        run_demo(root)
    except (OSError, ValueError) as exc:
        print(f"demo: {exc}", file=sys.stderr)
        return 1
    print(json.dumps({
        "mode": "FIXTURE", "status": "SCAFFOLD_DEMO",
        "outputs": [f"reports/demo/{name}" for name in (
            "concept-code-map.json", "guided-lesson.md", "learning-evidence.json"
        )],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
