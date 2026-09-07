> 历史保留：以下为 Phase 0 回归资产，不是当前比赛 MVP。新学习软件见 README.md 与 docs/rescope-decision.md。

# Synthetic Smoke Demo

Run `python scripts/tutor.py demo` from the checkout root after installing dev dependencies.
One predefined concept from `training-materials/onboarding.md` maps to one actual Python
function and an actual pytest. The function and test locations are found with AST;
the example and pytest actually run in a temporary copy. No model or network is used.
All outputs carry `mode: FIXTURE` and `status: SCAFFOLD_DEMO`.
