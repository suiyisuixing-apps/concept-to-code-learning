# 四人职责与入队状态

2026-09-08 基线：PR #56 已获 @fqf060420 正式 APPROVED 并由其合并；pre-rules-v0.2.0 固定在 e83a64d63a78f11534fbe51631775ceeb3885ccb。本文及 Sprint 1 合同通过独立 [Lead 准备 PR #58](https://github.com/suiyisuixing/concept-to-code-learning/pull/58) 交付；模块开发前确认该 PR 已经他人审核并合并。

2026-09-08 GitHub API 确认三名队员都已接受邀请并拥有 Write、无 Admin；未决邀请为 0。所有过时 waiting-for-collaborator 已移除，开放任务已分配到真实账号。下表为 API 分配快照；不是成员已完成任务的声明。

| 账号 | 角色 | 实际 Assignee Issues（含历史关闭） | 访问 |
| --- | --- | --- | --- |
| @suiyisuixing | Lead / Product / Skill / Integration | #1, #2, #3, #4, #5, #6, #27, #31, #35, #36, #37, #38, #52 | Owner / Admin |
| @inogi-sama | Document Workspace / Frontend | #7, #8, #9, #14, #29, #39, #40, #41, #42, #53 | Write（无 Admin） |
| @zchzbjklg | GitHub Code Intelligence | #15, #16, #17, #18, #19, #20, #21, #22, #32, #34, #43, #44, #45, #46, #47, #48, #54 | Write（无 Admin） |
| @fqf060420 | AI Tutor / Local Model / Evaluation | #10, #11, #12, #13, #23, #24, #28, #30, #49, #50, #51, #55 | Write（无 Admin） |

Sprint 1 按本轮用户要求将 #27 来源笔记持久化转交 Lead；Tutor 负责讲解输出，Document 负责笔记 UI。历史 #25/#26/#33 继续关闭，不重新分配。

CODEOWNERS 保留原角色规则，并为本次创建的 integration/ 和 AGENTS.md 添加 Lead 路径；公共 Schema 变更由 Lead 管理。

入队 Issue：#53/#54/#55。仅凭 API 更新“接受邀请”，其他已有勾选保留并注明证据等级。@fqf060420 普通评论自报本地安装及 Python 测试；该评论未绑定完整 head SHA，不能证明当前代码测试全部完成。另已核验其 2026-09-08T08:28:50Z 对 #56 的正式 APPROVED。2FA/Clone 的已有自报记录不冒充 Lead 独立核验；已通过 GitHub 核验其个人分支及代码修复 PR #57；该 PR 不等于清单要求的小型文档 PR，后者及他人审核、合并后删分支仍待完成。其最新 PR 自报 Windows 74 passed / 2 failed、demo 失败，原“运行测试”勾选不应解读为全部通过。

各人的下一步为 docs/codex-prompts/ 中对应提示词。PR #56 合并及 v0.2 标签已完成；合同准备 PR 先行，再 Document/GitHub 并行、Tutor 联合验收、Lead 最终集成。详见 sprint-1-first-real-vertical-slice.md。
