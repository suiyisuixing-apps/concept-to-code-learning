# HANDOFF — github_intelligence module

**Owner**: @zchzbjklg  
**Issue**: #67 (Full delivery: three-mode source discovery, retrieval and fixed-source verification)  
**Branch**: `feat/github-source-verification` (based on `feat/full-learning-integration` @ `90fb42f`)  
**Date**: 2026-09-10

## Delivered in this slice

### C1 — Module wiring and factory
- `github_intelligence/full.py`: `build_provider(settings)` returns a `GitHubSourceProvider`
  implementing `SourceProvider` from `full_learning/ports.py`.
- `github_intelligence/__init__.py`: exports `build_provider` and `GitHubSourceProvider`.
- The factory is synchronous; `httpx.AsyncClient` is created lazily on the first
  authorized network call, never during construction.

### C2 (partial) — Three-mode dispatch
- `specified_public`: fully implemented (search + verify).
- `public_search`: raises `NOT_IMPLEMENTED` (501) — tracked below.
- `local_authorized`: raises `NOT_IMPLEMENTED` (501) — tracked below.

### C4 — Precise source verification (specified_public)
- `github_intelligence/verifier.py`: SourceVerifier orchestrates
  repository URL parse → allowlist check → ref/commit resolution →
  raw file fetch → Python static AST symbol location → excerpt SHA256 →
  file SHA256 + git blob SHA → license detection from the same commit →
  CodeEvidence construction that passes the strict model_validator.
- `github_intelligence/github_client.py`: GitHubRawClient contacts only
  `raw.githubusercontent.com` and `api.github.com`; redirects are not followed
  across hosts; 401/403/404/429 mapped to SourceError; token never in messages.
- License detection probes LICENSE/LICENSE.md/LICENSE.txt/COPYING/NOTICE at the
  same commit; SPDX-grade identifiers (MIT, Apache-2.0, BSD-3-Clause, BSD-2-Clause,
  ISC, MPL-2.0, Unlicense) asserted from the title; unknown content withholds code.

### C5 (partial) — Local registry
- `github_intelligence/registry.py`: LocalRegistry returns host-configured
  handles only; rejects path escape via `..`, absolute paths, and symlinks
  leaving the authorized root.

### C7 (partial) — Tests
- `tests/github_intelligence/`: 43 tests covering specified_public happy path,
  authorization failures (no network, empty allowlist, repo not in allowlist),
  ref/file/symbol failures, license-unknown code withholding, registry escape
  rejection, capabilities, local_handles, dispatch for all three modes.
- All tests run offline with a FakeGitHubRawClient; no network required.

## Not delivered (tracked for the next slice)

| Section | Item | Status |
|---|---|---|
| C2 | public_search search + verify | NOT_IMPLEMENTED (501) |
| C2 | local_authorized search + verify | NOT_IMPLEMENTED (501) |
| C3 | Concept-term retrieval (file tree, code text, function, test ranking) | NOT_IMPLEMENTED |
| C5 | Dirty working-tree detection, file_sha256 for local reads | NOT_IMPLEMENTED |
| C6 | HTTP cache (repo/commit/file/range/hash scoped), rate-limit retry windows | NOT_IMPLEMENTED |
| C7 | Full failure matrix (pagination, timeout, cancel, cache isolation, malicious README) | NOT_IMPLEMENTED |

## Quality gate (local, Python 3.12.10, Windows 11)

| Check | Result |
|---|---|
| `ruff check .` | ✅ All checks passed |
| `pytest tests/github_intelligence/` | ✅ 43 passed |
| `python scripts/tutor.py doctor` | ✅ DONE, schema_count=6, errors=[] |
| `python scripts/tutor.py demo` | ✅ FIXTURE / SCAFFOLD_DEMO |
| `pytest -q` (full suite) | ⚠️ 296 passed, 9 failed, 2 errors |

### Full-suite failures (Lead-owned integration tests)

The 9 failures are in `tests/test_sprint1_integration.py`,
`tests/full_delivery/`, and `tests/test_text_encoding.py`. They expect the
github provider to remain `UnavailableProvider` (raising
`PROVIDER_NOT_IMPLEMENTED` 501). With this slice installed, the github
provider is now `GitHubSourceProvider` and returns `NETWORK_NOT_AUTHORIZED`
(403) when `network_authorized=False`, which is the correct behavior per
INTERFACES.md. These Lead-owned tests need to be updated to reflect the
github provider upgrade; they are outside this module's ownership boundary
and were not modified.

## Five-minute check

```bash
cd ~/Desktop/concept-to-code-learning
export PYTHONUTF8=1
./.venv/Scripts/ruff.exe check src/concept_to_code_learning/github_intelligence/
./.venv/Scripts/python.exe -m pytest tests/github_intelligence/ -q
./.venv/Scripts/python.exe scripts/tutor.py doctor
./.venv/Scripts/python.exe scripts/tutor.py demo
```

## Real vs Mock matrix

| Capability | Real | Mock/Fixture |
|---|---|---|
| specified_public verify (commit, file, AST, hash, license) | ✅ real logic | FakeGitHubRawClient returns frozen bytes |
| specified_public search (allowlist framework) | ✅ real logic | No network (allowlist-only) |
| public_search / local_authorized | ❌ NOT_IMPLEMENTED | n/a |
| GitHub token | read from C2C_GITHUB_TOKEN via ProviderSettings | test token is a placeholder string |
| httpx.AsyncClient | created lazily on first authorized call | never created in tests (FakeGitHubRawClient) |
