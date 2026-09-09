> 2026-09-09 当前执行范围： [完整学习版](full-delivery/PLAN.md)；[新接口与职责](full-delivery/INTERFACES.md)。以下旧阶段说明保留作兼容和历史参考。

# 本地 Fixture API

所有成功的 demo/notes 响应及预留接口都标记 `mode: FIXTURE`、`status: SCAFFOLD_DEMO`。

| 接口 | 行为 |
| --- | --- |
| GET /health | health=ok、版本、Fixture 状态 |
| GET /api/demo/session | 合成讲义、页码、初始问题、四档难度与能力 false 标记 |
| POST /api/learning/explain | question + document_context + explanation_level；返回符合 grounded-explanation 的固定讲解 |
| POST /api/github/search | HTTP 501 / NOT_IMPLEMENTED / 空 results，无网络 |
| POST /api/github/verify | HTTP 501 / NOT_IMPLEMENTED / NEEDS_CONFIRMATION，无通用核验 |
| POST /api/notes | explanation ID + title + user_text + save_requested_by_user=true；201 返回新增笔记 |
| GET /api/notes | 读取本地持久化笔记及两类来源快照 |

解释仅接受合成文档中的真实页/原文选区与正确 SHA-256，错误或不支持的问题返回 422/NEEDS_CONFIRMATION。缺失解释 ID 的保存返回 404；用户没有显式保存、空标题、超限字段或伪造来源字段返回 422。保存只接受服务端生成的解释 ID，从数据库读取真实来源，不能用前端提交内容替换。

GET 不创建笔记，再次提问不改变笔记；没有 PUT/DELETE 笔记端点。显示读取错误并允许重试，不把失败标为成功。SQLite 无账户隔离，仅用于单用户 loopback Fixture。

## 接缝与治理

公共 API/Schema 变更由 Lead 审核，只有 @suiyisuixing 可以合并。Lead 自有 PR 经人工自检、Codex 审计与 required CI 后可自行合并，无需外部批准；所有 PR 不得有 P0/P1 阻塞。

`/api/sprint-1` 的版本合同和独立快照表由 PR #58 引入，使用前核验其 main 合并状态；旧 `/api/notes` 保留原记录，不补造旧 hash。真实 PPTX、通用 GitHub 核验和模型仍须独立实现与验收。见 [Sprint 1](sprint-1-first-real-vertical-slice.md) 和 [治理政策](governance/lead-controlled-merge-policy.md)。
