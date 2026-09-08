# Sprint 1 合同审查与兼容性记录

基线：pre-rules-v0.2.0 / e83a64d63a78f11534fbe51631775ceeb3885ccb，已由真实队员审核并合并。此 PR 冻结独立 `contract_version: sprint-1`，主 Issue #5；正式共同基线仍须等待本 PR 的他人审核与合并。

| 活动合同 | 审查结论 | 本 PR 的最小增量与原因 |
| --- | --- | --- |
| DocumentContext | 原版缺 file_hash、visible_text | 新版增加二者、mode、contract_version，约束当前可见文本与来源版本；限定 PPTX 或明确 MARKDOWN_FIXTURE |
| GitHubCodeSource | 原版元数据已满足需求 | 保留所有字段并加版本；Verified 必须 public，禁止状态混淆，并验证请求绑定、行区间、片段 hash；核验回执来自服务端端口 |
| GroundedExplanation | 原版只有固定讲解 | 新版增加 unsupported_claims、provider_mode、版本；嵌套新版上下文/来源，引文加 file_hash；本 Sprint 限两档、单来源、不执行代码 |
| SavedNote | 原快照名 grounded_explanation | 新版增加 explanation_snapshot 与版本，保留旧别名；两个快照与顶层来源必须相等；个人文字不由模型写入 |
| LearningConcept | 无需重做提取算法 | 根文件保持原样；新版解释内的定义仅同步新版 DocumentContext |
| RunnableExample | 已要求真实运行证据 | 根文件保持原样；新解释的 runnable_example_status 固定 NOT_RUN，未来执行扩展另经 Lead 审核 |

## 文件和版本

原 `schemas/*.schema.json` 六文件、旧验证器、旧 API 与旧 Fixture 数据均保留。新增四文件位于 `schemas/sprint-1/`，由 `integration/contracts.py` 验证。新旧 required 字段与 additionalProperties=false 不兼容，因此不直接替换旧根合同。旧数据通过原验证器读取，新数据必须显式版本；不自动迁移旧记录。

每个新 Schema 是独立可验证文件。嵌套通过该文件内部 `$defs` 引用，禁止远程/跨文件 `$ref`。测试比较内嵌 DocumentContext/GitHubCodeSource 与独立定义一致，避免同名合同漂移。

DocumentContext 的 file_hash 是源文件原始字节 SHA-256。Fixture 的真实来源文件是 `demo/learning/document.json`，显示文件名沿用原讲义名称，不把它标为 PPTX。visible_text 为当前页段落以两个 LF 连接的原字符串；选区必须为其中连续子串，UTF-8 SHA-256 与 selected_text_hash 一致；空选区的 hash 为 null。PPTX Provider 要自行约定稳定的可见文本顺序，current_slide 从 1 开始，current_page=null，不修改原字节。

## 来源与完成状态

GitHubCodeSource 保留原始仓库 URL、固定 SHA、路径、Python 符号及含装饰器的闭区间行号、最小片段和许可证。Schema 的合法性不能证明已访问 GitHub；`VerifiedSource` 是可信服务端 verifier 对七项核验的进程内回执。Service 检查回执属于该请求、检查齐全、源身份/SHA/行数/hash一致；不能接受客户端上传回执。网络/API/AST/许可真实性由后续 GitHub 实现和独立 opt-in 验收证明。

FixtureGitHubVerifier 只接受已有快照的精确 repo/SHA/path/symbol，不响应任意仓库或 main。未验证来源不能进入 Tutor。没有执行模块，不允许新解释或其来源声称 VERIFIED_RUNNABLE。根 RunnableExample 原有证据规则仍被旧测试覆盖。

unsupported_claims 非空、引文不符、Tutor 替换来源或问题都拒绝进入成功/保存路径。错误输出提供 code/stage，不把私有正文或底层异常拼进报错。只有 context/source 实际 LIVE 且 provider_mode=openai_compatible 时才允许 LIVE/GROUNDED_ANSWER；任何 Fixture 输入或固定讲解都保留 FIXTURE/SCAFFOLD_DEMO。元数据门禁不等于模型语义 grounding 评测完成，后者由 #51 负责。

## 笔记兼容性和快照

复用原 NoteStore 的 SQLite 文件和连接：`fixture-notes.sqlite3`。新增 `sprint_explanations`、`sprint_notes` 表，旧 explanations/notes 表不回写；原 `/api/notes` 读取历史笔记，新 `/api/sprint-1/notes` 读取新版本。UI 本轮仍使用旧 API，未来迁移 UI 时需明确提供两个读取入口，不伪造旧字段。

解释先存为服务端快照；显式 save 请求只接受 ID、title、user_text 和 true，随后从数据库复制完整解释、双来源、hash、SHA、许可证和时间。没有 UPDATE/DELETE，重复保存创建新 ID，不修改旧记录。数据库写入失败回滚并返回失败。测试修改返回对象、文档状态、仓库状态，再用新进程读取，验证旧快照及个人文字不变；兼容测试同时验证旧表的原始 JSON 不变。

## 可执行样例与证据

`GET /api/sprint-1/session` 的 `fixture_example` 是完整 ExplainRequest（文档句柄+页/选区、SourceRequest、question、explanation_level），POST 到 `/api/sprint-1/learning/explain` 得到新 GroundedExplanation；将返回 ID 和显式保存请求 POST 到 `/api/sprint-1/notes` 得到完整 SavedNote。`tests/test_sprint1_integration.py` 逐项验证四合同所有 required 字段及这一端到端流程。

新增测试与最终通过数量见本 PR 正文；不得将测试矩阵编号数当通过数。旧 CLI doctor/demo 覆盖原基线；新版本合同与服务由 pytest 中的 Sprint 测试覆盖。所有默认验收离线，真实 PPTX/GitHub/模型仍是后续角色任务。

## 新增文件的跨平台边界

新增合同读取显式 UTF-8，新版存储在事务完成或异常后都关闭 SQLite 连接；测试模拟 GBK 默认编码并验证连接关闭。队员另有 [PR #57](https://github.com/suiyisuixing/concept-to-code-learning/pull/57) 修复既有模块的 UTF-8 问题，并自报旧存储在 Windows 的清理失败；本 PR 未吸收其变更。当前完整套件的本地通过证据来自 macOS，CI 来自 Ubuntu；不宣称 Windows 全套验证完成。
