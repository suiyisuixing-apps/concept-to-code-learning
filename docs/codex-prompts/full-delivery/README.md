> 2026-09-21 权限更新：[当前共同维护政策](../../governance/team-maintained-policy.md)优先。项目已公开于 `suiyisuixing-apps/concept-to-code-learning`；四人均为仓库 Admin，均可审核和合并通过检查的 PR，无需 Lead 专门批准。模块分工不是文件权限限制；不得绕过 CI，Codex 不代填人工检查。下文保留原任务书，其中私有、仅 Lead 合并和成员 Write 条款已失效，其他功能及证据要求保留。

# 完整模块一次性委派

本轮任务书以 full-delivery-v1 为共同协议，取代旧 Sprint 1小切片的有效开发范围；旧文件保留作历史。

| 角色 | 可单独发送的文件 | 代码入口 |
|---|---|---|
| Lead | 01_LEAD_FULL_EXECUTION.md | full_contracts / full_learning / root API / store / Skill |
| inogi-sama | 02_INOGI_FULL_EXECUTION.md | documents/full.py + apps/web |
| zchzbjklg | 03_ZCHZBJKLG_FULL_EXECUTION.md | github_intelligence/full.py |
| fqf060420 | 04_FQF060420_FULL_EXECUTION.md | tutor/full.py + runtime / evals / DGX |

01 是用户实际附件的原文副本。02–04 是 Lead 按已提供范围和 01 公共协议整理的新任务书，未冒充缺失下载引用中的原始文件。COMMON_PROTOCOL.md 保存公共 A/B 原文，实际稳定字段以 full_contracts/models.py、生成 Schema 和 OpenAPI 为准，具体接缝见 docs/full-delivery/INTERFACES.md。

三名成员在各自 Codex 中并行实施自己的模块；本任务没有启动或冒充他们的代理、没有发送私人消息。GitHub主Issue是完整任务的发布记录，交付事实仍由实际PR证明。
