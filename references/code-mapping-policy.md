# 概念到代码证据

活动策略见 github-source-policy.md。新代码引用使用 github-code-source.schema.json，验证仓库、Commit、路径、符号、行号、许可证和最小片段 hash。AST 结果不能证明代码可运行或完整业务行为。

Phase 0 的旧 VERIFIED 字段仅在 schemas/legacy 与旧回归中保留；新 UI 使用具体 GitHub/本地来源状态和独立的 NOT_RUN/VERIFIED_RUNNABLE。
