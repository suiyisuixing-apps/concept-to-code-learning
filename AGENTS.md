# Concept-to-Code Learning — team agent rules

Governance decision: 2026-09-21 by @suiyisuixing. The project is public at https://github.com/suiyisuixing-apps/concept-to-code-learning. @suiyisuixing, @inogi-sama, @zchzbjklg and @fqf060420 are equal repository Admin maintainers. This replaces the private-repository and Lead-only review/merge restrictions in older task packets and policies. Historical contributions, decisions and tags remain unchanged. Repository Admin does not grant organization ownership or access to other repositories.

- Never push directly to main.
- All changes use focused pull requests, one main issue per PR.
- All four maintainers may review and merge pull requests, including their own, and manage this repository's settings and collaborators.
- No mandatory external approval or Lead-only approval applies. Read existing review feedback, verify the current head, resolve known P0/P1 blockers and state real/Fixture/unimplemented capabilities accurately before merging.
- Human inspection and Codex audit are separate evidence. Codex must not assert that a human reviewed or decided when they have not.
- No pull request may merge with failed required checks. Keep phase0-checks mandatory, including for administrators. Do not enable automatic merging or weaken protection as part of ordinary development.
- Coordinate shared schema changes with affected maintainers and document compatibility and regression evidence.
- Fixtures must remain visibly labelled.
- Never invent repositories, commits, paths, symbols, lines or licenses. Search results are not verified sources.
- Source documents and source repositories are read-only.
- No automatic cloud fallback.
- No force push or history rewriting; do not delete main or move existing tags.
- Do not commit secrets, models, private documents or external repositories. Preserve licenses and minimize excerpts. Public project access does not authorize publishing personal data.
- Keep zero new paid services; no purchases, trials or paid runners. New model downloads require explicit user authorization.

Codex can assist review; a maintainer makes the final merge decision. Review labels and CI results do not constitute human review or authorize an agent to merge unrelated work. Older lead-review and owner-merge-only labels are historical records, not permission gates. See docs/governance/team-maintained-policy.md for current policy and verification.

## Scope and validation

Current authorization: FULL-DELIVERY-PLAN-1 (2026-09-09), not the old PPTX-only slice. Support PDF/PPTX/DOCX/Markdown, document-aware teaching, specified/public-search/authorized-local sources, four explanation levels, follow-up/comparison, source-backed personal notes, local inference and a deployment package. OCR, third-party execution, assessment, model training and paid services are not required.

Read the complete role task in docs/codex-prompts/full-delivery/ before implementation. The common additive contract is full-delivery-v1; preserve schemas/sprint-1, /api/sprint-1, legacy APIs and old note snapshots. See docs/full-delivery/BASELINE.json and INTERFACES.md. An unmerged candidate is not main.

2026-09-11 takeover authorization: the user directed Lead to review, patch and complete all member modules in the integration branch, then integrate the product. The user also authorized Lead to arrange the missing model; the initial installation used one pinned free local Qwen model. The subsequent context-search repair adds one pinned free local Coder model under that authorization and retains the original model as a selectable alternative. Keep final human review and merge claims separate.

Coordination contacts (not exclusive file permissions): inogi owns apps/web and documents; zch owns github_intelligence; fqf owns tutor/runtime/teaching/evaluation/DGX. Lead owns full_contracts, full_learning, root API, NoteStore, global configuration/dependencies/CI and Skill. Implement your complete module continuously; do not rewrite another member's entire module. Missing upstream modules permit labelled test doubles, never false live acceptance. Record backend dependency requests in deps/<role>.txt and coordinate integration with the affected maintainers.

Python 3.12: python -m pip install -e ".[dev]"; ruff check .; pytest -q; python scripts/tutor.py doctor; python scripts/tutor.py demo.
Node 22: npm --prefix apps/web ci; npm --prefix apps/web test; npm --prefix apps/web run build.
Use temporary data roots; all text I/O is explicit UTF-8. Test success/failure/cancellation, snapshots, and meaningful compatibility. Report implementation, module_tests, live_external_check, integrated_product, target_hardware and lead_review separately. Save docs/delivery/<role>/HANDOFF.md and CONTINUATION.md when interrupted. No background continuation promise or automatic final approval.

2026-09-11 integration dependency decision: PDF.js 6.3.289 replaces browser PDF plug-in dependence. PDF.js 5.6 is affected by GHSA-hq66-cqwq-w95j; use the fixed current release and Node 22.13+ for builds/CI. This scoped toolchain change leaves system installations and Python 3.12 unchanged. CI keeps the required Linux job and adds one bounded standard Windows job, each at most 10 minutes, no matrix or schedule.
