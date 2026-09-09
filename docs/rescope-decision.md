# Phase 0.5 产品重构决策

日期：2026-09-07。依据：用户明确要求的文档学习、旁栏讲解、真实 GitHub 代码引用和个人笔记。

## 错误与纠正

Phase 0 被定位为企业新员工入职、单一私有仓库讲解、强制练习、隐藏评分、学习证据与文档漂移。这缩窄了用户人群并将学习帮助变成员工考核，与当前页/选区的日常技术学习需求不一致。

现在产品为 Concept-to-Code Learning。主链是文档上下文 → 分级讲解 → 经过验证的代码证据 → 用户主动保存笔记。保留可选示例验证与未来多仓库比较；不自动修改来源仓库。

## 保留与退役

保留 Git 全历史、私有设置、Issues、Actions、分支保护、基线标签；保留 Python 3.12、CLI doctor/demo、现有 65 项回归覆盖的契约/来源/失败路径思路、合成 fixture 与成本边界。旧四契约转入 schemas/legacy，旧 smoke 执行仍可复现。

#25/#26/#33 以 not planned 退出 MVP，关闭前追加指定 SUPERSEDED_BY_PRODUCT_RESCOPE 评论。#21/#34 降为 post-MVP/P2，不阻塞 M4。#27 改为来源笔记，#29 改为三栏 UI；#22 改为公开许可代码样例来源，不限定 LLM Security Lab。

## 不可变基线与迁移

- 仓库 ID：1360182264；旧名 concept-to-code-onboarding；新名 concept-to-code-learning。直接重命名，未新建仓库。
- 基线 Commit：8c487316ccf598b0a549803d3cff3814302633c3。
- 保留标签：pre-rules-v0.1.0；tag object ddbe1b7a6b0f7edb10093c66ab95eed7b5e87cdc。
- 代码分支：rescope/concept-to-code-learning；所有代码通过 PR 进入 main。
- 本轮实现 Commit：[fee31de34e0ea2f156171df88fc113f049e6518b](https://github.com/suiyisuixing/concept-to-code-learning/commit/fee31de34e0ea2f156171df88fc113f049e6518b)，日期 2026-09-07。
- 正式 PR：[#56 — [Rescope] Convert project into Concept-to-Code Learning](https://github.com/suiyisuixing/concept-to-code-learning/pull/56)。后续补充文档 Commit 保留在此 PR 历史中；本文件不是自动刷新的合并状态源。未获得真实队员批准并正常合并前状态为 BLOCKED_BY_REQUIRED_REVIEW。
- 只有另一名真实成员批准、必需 CI 成功并正常合并后才可创建 pre-rules-v0.2.0。没有 GitHub Release。

## 当前交付边界

0.2.0.dev0 实现 React/Vite 三栏、FastAPI Fixture API、六契约、固定 FastAPI 来源与本地 SQLite 来源笔记。Fixture 始终显式标记。真实解析、通用检索与验证、模型、DGX、比较和新来源运行仍是后续工作。单条来源核验不是通用实现。

## 2026-09-09 治理变更说明

上文保留当时的历史范围与状态，不作为当前审批门禁。此日起只有 @suiyisuixing 最终审核与合并 main；成员 PR 由 Lead 审核，Lead 自有 PR 经人工自检、Codex 审计和 required CI 后可自行合并，无需外部批准。PR/CI、禁止直接 Push/Force Push/删除 main 仍保留。参见 [治理政策](governance/lead-controlled-merge-policy.md)。Project 是否已创建仍需单独核验，治理迁移不证明 Project 完成。
