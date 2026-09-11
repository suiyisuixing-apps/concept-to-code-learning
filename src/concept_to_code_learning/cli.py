"""Small checkout-oriented command line entry point."""

import argparse
import json
import shutil
import sys
import tempfile
from pathlib import Path

from concept_to_code_learning.scaffold import doctor, run_demo


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Concept-to-Code Learning · local software")
    parser.add_argument("command", choices=("doctor", "demo", "serve", "start"))
    parser.add_argument("--port", type=int, default=8766)
    parser.add_argument("--data-dir", type=Path)
    args = parser.parse_args(argv)
    root = Path.cwd().resolve()
    if args.command in {"serve", "start"}:
        if not 1 <= args.port <= 65535:
            parser.error("Port must be between 1 and 65535")
        if args.command == "start" and not (root / "apps/web/dist/index.html").is_file():
            print("请先安装依赖并运行 npm --prefix apps/web run build。", file=sys.stderr)
            return 1
        import uvicorn

        from concept_to_code_learning.api import create_app

        print(f"本地学习软件：http://127.0.0.1:{args.port}\n"
              f"真实能力状态：http://127.0.0.1:{args.port}/api/learning/v1/capabilities\n"
              "阅读器与笔记可直接使用；模型连接状态见页面提示。按 Ctrl+C 停止。", flush=True)
        uvicorn.run(create_app(root=root, data_dir=args.data_dir), host="127.0.0.1", port=args.port)
        return 0
    if args.command == "doctor":
        result = doctor(root)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["status"] == "DONE" else 1
    try:
        output = root / "reports/learning-demo"
        if output.is_symlink() or (root / "reports").is_symlink():
            raise ValueError("NEEDS_CONFIRMATION: generated reports must not be symlinks")
        if output.exists():
            shutil.rmtree(output)
        run_demo(root)
        from concept_to_code_learning.store import NoteStore
        from concept_to_code_learning.tutor.fixture import QUESTION, FixtureTutor

        tutor = FixtureTutor(root)
        explanation = tutor.explain(QUESTION, tutor.context(), "Beginner")
        with tempfile.TemporaryDirectory(prefix="c2c-demo-notes-") as temp:
            store = NoteStore(Path(temp), tutor.schemas)
            store.remember(explanation)
            note = store.save(explanation["grounded_explanation_id"],
                              "Fixture verification note", "Synthetic test only")
            assert NoteStore(Path(temp), tutor.schemas).list()[0] == note
        output.mkdir(exist_ok=True)
        (output / "grounded-explanation.json").write_text(
            json.dumps(explanation, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (output / "saved-note.json").write_text(
            json.dumps(note, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except (OSError, ValueError) as exc:
        print(f"demo: {exc}", file=sys.stderr)
        return 1
    print(json.dumps({
        "mode": "FIXTURE", "status": "SCAFFOLD_DEMO",
        "learning_outputs": ["reports/learning-demo/grounded-explanation.json",
                             "reports/learning-demo/saved-note.json"],
        "outputs": [f"reports/demo/{name}" for name in (
            "concept-code-map.json", "guided-lesson.md", "learning-evidence.json"
        )],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
