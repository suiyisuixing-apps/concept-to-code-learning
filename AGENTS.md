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

Current authorization: FULL-DELIVERY-PLAN-1 (2026-09-09), not the old PPTX-only slice. Support PDF/PPTX/DOCX/Markdown, document-aware teaching, specified/public-search/authorized-local sources, four explanation levels, follow-up/comparison, source-backed personal notes, local inference and a deployment package. OCR, third-party execution, assessment, model training and paid services are not required.

Read the complete role task in docs/codex-prompts/full-delivery/ before implementation. The common additive contract is full-delivery-v1; preserve schemas/sprint-1, /api/sprint-1, legacy APIs and old note snapshots. See docs/full-delivery/BASELINE.json and INTERFACES.md. An unmerged candidate is not main.

Ownership: inogi owns apps/web and documents; zch owns github_intelligence; fqf owns tutor/runtime/teaching/evaluation/DGX. Lead owns full_contracts, full_learning, root API, NoteStore, global configuration/dependencies/CI and Skill. Implement your complete module continuously; do not rewrite another member's entire module. Missing upstream modules permit labelled test doubles, never false live acceptance. Backend dependency requests belong in deps/<role>.txt until Lead integration.

Python 3.12: python -m pip install -e ".[dev]"; ruff check .; pytest -q; python scripts/tutor.py doctor; python scripts/tutor.py demo.
Node 20: npm --prefix apps/web ci; npm --prefix apps/web test; npm --prefix apps/web run build.
Use temporary data roots; all text I/O is explicit UTF-8. Test success/failure/cancellation, snapshots, and meaningful compatibility. Report implementation, module_tests, live_external_check, integrated_product, target_hardware and lead_review separately. Save docs/delivery/<role>/HANDOFF.md and CONTINUATION.md when interrupted. No background continuation promise or automatic final approval.
