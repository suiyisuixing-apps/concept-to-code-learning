"""Generate public schemas and OpenAPI from the same Python DTOs; --check detects drift."""

import argparse
import hashlib
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from concept_to_code_learning.full_contracts import models as m  # noqa: E402

MODELS = [m.DocumentRecord, m.DocumentUnit, m.DocumentContext, m.ContextRequest, m.ActivateContext,
          m.SourceScope, m.SourceQuery, m.SearchCandidate, m.SearchResult, m.CodeEvidence,
          m.TeachingPlan, m.GroundedExplanation, m.ExplanationRequest, m.ExplanationResult,
          m.SessionRecord, m.SearchRequest, m.VerifyRequest, m.SaveNoteRequest, m.EditNoteRequest,
          m.DeleteNoteRequest, m.SavedNote, m.NoteList, m.Capabilities, m.LearningErrorResponse]


def generated():
    artifacts = {}
    for model in MODELS:
        schema = model.model_json_schema()
        schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
        artifacts[f"schemas/full-delivery-v1/{model.__name__}.schema.json"] = schema
    from concept_to_code_learning.api import create_app
    with tempfile.TemporaryDirectory(prefix="c2c-schema-") as folder:
        app = create_app(Path(folder), root=ROOT)
        artifacts["docs/full-delivery/openapi.json"] = app.openapi()
    text = {path: json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
            for path, value in artifacts.items()}
    index = {"contract_version": "full-delivery-v1", "generated_from": "full_contracts/models.py",
             "runtime_invariants": "See INTERFACES.md; hashes/authorization require server validation.",
             "artifacts": {path: hashlib.sha256(value.encode("utf-8")).hexdigest()
                           for path, value in text.items()}}
    text["schemas/full-delivery-v1/index.json"] = json.dumps(index, indent=2, sort_keys=True) + "\n"
    return text


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    stale = []
    for path, text in generated().items():
        target = ROOT / path
        if args.check:
            if not target.exists() or target.read_text(encoding="utf-8") != text:
                stale.append(path)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text, encoding="utf-8")
    print(json.dumps({"status": "STALE" if stale else "CURRENT", "stale": stale}))
    return 1 if stale else 0


if __name__ == "__main__":
    raise SystemExit(main())
