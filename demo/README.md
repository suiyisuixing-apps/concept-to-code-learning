# Synthetic Smoke Demo

Run `python scripts/tutor.py demo` from the checkout root after installing dev dependencies.
One predefined concept from `training-materials/onboarding.md` maps to one actual Python
function and an actual pytest. The function and test locations are found with AST;
the example and pytest actually run in a temporary copy. No model or network is used.
All outputs carry `mode: FIXTURE` and `status: SCAFFOLD_DEMO`.
