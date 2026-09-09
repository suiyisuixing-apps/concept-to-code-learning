# Concept-to-Code Learning — team agent rules

Governance decision: 2026-09-09 by @suiyisuixing. This policy replaces mandatory peer approval and author self-merge prohibitions for Lead-authored PRs. PR #56 and pre-rules-v0.2.0 at e83a64d63a78f11534fbe51631775ceeb3885ccb are preserved historical evidence, not recurring peer-review gates.

- Never push directly to main.
- All changes use focused pull requests, one main issue per PR.
- Only @suiyisuixing may merge into main.
- Teammates must not merge their own or others' pull requests, enable auto-merge or merge queue, or change protection/rulesets.
- Lead-authored PRs do not require external approval.
- Lead-authored PRs require successful CI, Lead self-review and Codex audit; no known P0/P1 blocker and accurate real/Fixture/unimplemented claims.
- Lead self-review includes human inspection of key files. Codex must not assert that a human reviewed or decided when they have not.
- Teammates may provide non-blocking comments and suggestions; Lead reads them before deciding.
- Teammate-authored PRs require Lead review before merge.
- No pull request may merge with failed required checks. Keep phase0-checks mandatory, including for administrators.
- Do not modify shared schemas without Lead approval. Document compatibility and regression evidence.
- Fixtures must remain visibly labelled.
- Never invent repositories, commits, paths, symbols, lines or licenses. Search results are not verified sources.
- Source documents and source repositories are read-only.
- No automatic cloud fallback.
- No force push or history rewriting; do not delete main or move existing tags.
- Do not commit secrets, models, private documents or external repositories. Preserve licenses and minimize excerpts.
- Keep the repository private and zero new paid services; no purchases, trials, paid runners or model downloads.

Codex can assist review; the final decision belongs to @suiyisuixing. Review labels and CI results do not constitute that decision. Member PRs start with lead-review:pending; Lead maintains the decision labels. See docs/governance/lead-controlled-merge-policy.md for live verification and rollback.

## Scope and validation

Sprint 1 targets authorized PPTX, one explicitly selected public GitHub repository, verified Python source, grounded explanations and explicit source-backed notes. No PDF/DOCX/OCR, global search, private-source retrieval, multi-repository comparison, exercises, drift, DGX deployment or fine-tuning in this sprint. The application remains Fixture until corresponding real providers have implementation and execution evidence. PR #58 owns versioned contracts; do not assume an unmerged PR is available on main.

Use the role branch and main issue in docs/codex-prompts/. Lead owns contracts, API integration and NoteStore; Document owns PPTX and frontend; GitHub owns source verification; Tutor owns explanation/providers/evaluation. Do not complete another member's entire module or automatically start their tasks.

Python 3.12: python -m pip install -e ".[dev]"; ruff check .; pytest -q; python scripts/tutor.py doctor; python scripts/tutor.py demo.
Node 20: npm --prefix apps/web ci; npm --prefix apps/web test; npm --prefix apps/web run build.
Add meaningful positive and failure-path tests for behavior changes. Use temporary data directories; record commands, exit codes and actual counts. Offline Fixture tests cannot establish live document/network/model completion. Save immutable source snapshots only on explicit user action. Existing personal notes must remain unchanged.
