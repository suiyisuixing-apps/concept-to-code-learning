# 本地 Fixture API

以下 Phase 0.5 成功的 demo/notes 响应及预留接口都标记 `mode: FIXTURE`、`status: SCAFFOLD_DEMO`。

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

## Sprint 1 版本化接口

`/api/sprint-1` 使用新增四合同与独立版本表，旧 `/api/notes` 继续读取原记录；不会给旧快照补造 file_hash。完整 API、Provider 选择和错误表见 [Sprint 1 文档](sprint-1-first-real-vertical-slice.md)。响应中的 `FIXTURE` 是证据模式，`FAILED` 明确表示失败。
