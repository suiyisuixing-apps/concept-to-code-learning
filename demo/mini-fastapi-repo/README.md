> 历史保留：以下为 Phase 0 回归资产，不是当前比赛 MVP。新学习软件见 README.md 与 docs/rescope-decision.md。

# Tiny Python service fixture

`app.py` contains a FastAPI-style domain helper, `can_view_profile`, without a
FastAPI dependency or HTTP server. `example.py` checks expected positive and negative
results. `tests/test_app.py` is the deterministic pytest used by the demo. This
directory is synthetic and intentionally is not a nested Git repository.
