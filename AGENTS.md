# Concept-to-Code Learning — team agent rules

Baseline: PR #56 was formally approved and merged by @fqf060420 on 2026-09-08. pre-rules-v0.2.0 points to e83a64d63a78f11534fbe51631775ceeb3885ccb. Sprint changes require a separate reviewed PR.

- Never push directly to main.
- One focused issue per branch and pull request.
- Do not change shared schemas without Lead approval. Record each approved change, compatibility strategy, and regression tests. This sprint's requested minimum contract additions are authorized for the Lead preparation PR only after its baseline gates.
- Never invent repositories, commits, paths, symbols, lines, or licenses.
- Search results are not verified sources.
- Fixtures must remain visibly labelled.
- Source documents and source repositories are read-only.
- No automatic cloud fallback.
- Add tests for every behavior change.
- Run Python and frontend checks before requesting review.
- Never approve or merge your own pull request.
- Do not commit secrets, models, private documents, or external repositories.
- Minimize copied third-party code and preserve license information.

## Scope and gates

The first sprint supports authorized PPTX, one explicitly selected public GitHub repository, verified Python source, grounded explanations, and explicit source-backed notes. No PDF/DOCX/OCR, global search, private repositories, multi-repository comparison, exercises, drift, DGX deployment, model downloads or fine-tuning.

Use the role branch and main issue in docs/codex-prompts/. The Lead owns contracts, API integration and NoteStore; Document owns PPTX and frontend; GitHub owns source verification; Tutor owns explanation/providers/evaluation. Do not complete another member's entire module or automatically start their tasks.

Before development, verify PR #56 has a real non-author APPROVED review, successful required CI, normal merge, and the immutable pre-rules-v0.2.0 baseline. A comment saying Approve is not approval. Never lower protection, force push, rewrite history, move old tags, create Releases or start paid/trial services. Explicit user authorization governs the separate Phase 0.5 merge procedure; these no-self-merge rules apply to the team's Sprint PRs.

## Validation

Python 3.12: python -m pip install -e ".[dev]"; ruff check .; pytest -q; python scripts/tutor.py doctor; python scripts/tutor.py demo.
Node 20: npm --prefix apps/web ci; npm --prefix apps/web test; npm --prefix apps/web run build.
Use temporary data directories. Record executed commands, exit codes and actual counts. Offline Fixture tests cannot establish live document/network/model completion. Do not infer that sources have run because they are verified. Save immutable source snapshots only on explicit user action.
