# Sprint 1：第一个真实纵向切片

2026-09-08 基线：PR #56 已获 @fqf060420 正式 APPROVED 并由其合并；pre-rules-v0.2.0 固定在 e83a64d63a78f11534fbe51631775ceeb3885ccb。本文及 Sprint 1 合同通过独立 [Lead 准备 PR #58](https://github.com/suiyisuixing/concept-to-code-learning/pull/58) 交付；模块开发前确认该 PR 已经他人审核并合并。

## 用户故事与唯一场景

学习者上传一份自己拥有或获授权的真实 PPTX，打开某一张 Slide，选中其中一段技术文字并提问。系统只从用户明确指定的一个公开 GitHub 仓库寻找代码，固定 Commit，验证文件、Python 符号、行号、片段与许可证，再用 PPT 和代码联合解释。用户主动保存个人文字、解释和两类来源，刷新或重启后仍可读。

Real PPTX → Current Slide → Selected Text → DocumentContext → User Question → Verified GitHubCodeSource → GroundedExplanation → Source-backed SavedNote。

本期不做 PDF、DOCX、OCR、全网自动 GitHub 搜索、多仓库、私有 GitHub、自动修改来源、练习考试、漂移检查、DGX 部署、微调、LMS 或移动 App。开发与 CI 只用合成内容、自制 PPTX 和 Mock；真实学校/企业资料不进 Git。

## 四人输入输出与主任务

| 角色 | 输入 | 输出 | 主任务与分支 |
| --- | --- | --- | --- |
| @suiyisuixing / Lead | 现有六 Schema、各 Provider、显式保存请求 | 最小合同、接口、VerticalSliceService、NoteStore、集成验收 | #5（合同），#27（笔记），#52（最终验收）；feat/sprint-1-integration-contracts |
| @inogi-sama / Document | 授权 PPTX、Slide、选区 | DocumentContext、上传/阅读/选区 UI、只读文件证据 | #7，关联 #40/#14/#39；feat/pptx-current-slide |
| @zchzbjklg / GitHub | 指定公开仓库、Ref/Commit、文件、可选符号、联网授权 | 经过验证的 GitHubCodeSource 与最小片段 | #46，关联 #43/#47；feat/github-source-verification |
| @fqf060420 / Tutor | DocumentContext、已核验来源、问题、级别 | 两档 GroundedExplanation、Fixture 与 OpenAI-compatible 接口、对照评测 | #49，关联 #50/#51；feat/grounded-explanation |

#31 保留总验收入口，引用 #52，不开发第二条重复流水线。#27 本轮按用户指令由 Tutor 转交 Lead；Tutor 输出解释，Document 负责笔记交互，Lead 负责保存可信快照。

## 四个公共合同

详见 [合同审查与兼容方案](sprint-1-contract-review.md)。四个版本化合同已在本 PR 的 schemas/sprint-1/ 实现，原六个根合同保持兼容；他人审核并合并后成为团队共同基线。

| 合同 | Sprint 1 最小内容 |
| --- | --- |
| DocumentContext | document_id、file_name、source_type、file_hash、current_slide、current_page、current_section、visible_text、selected_text、selected_text_hash |
| GitHubCodeSource | 沿用 owner/name/URL/visibility、完整 Commit、路径、符号/类型、起止行、片段/hash、许可证/URL、检索时间、核验状态/方法、相关性、mode |
| GroundedExplanation | 保留原字段，新增 unsupported_claims、provider_mode；document_context 与双来源必须来自同一请求的可信 Provider |
| SavedNote | 保留个人正文、ID、时间、双来源，新增 explanation_snapshot；既有 grounded_explanation 作为兼容字段，旧数据库记录不回写 |

真实文档的文件 hash 是原 PPTX 字节的 SHA-256；当前 Fixture 的 file_hash 对应 demo/learning/document.json 原始字节。选区 hash 是协议约定 UTF-8 文本字节的 SHA-256。先定义文本抽取和换行规则，再验证 selected_text 属于当前 visible_text；不得为通过校验偷偷重写原文件或伪造旧记录的 hash。Slide 从 1 开始；PPTX 的 current_page 为 null，current_section 可以为 null。

来源“已核验”由可信服务端验证过程决定，客户端标签和 Schema 合法性本身不能证明仓库/符号真实。未运行示例始终 NOT_RUN。

## 模块接口

接口、DTO、Fixture 与服务已放入 src/concept_to_code_learning/integration/，CODEOWNERS 已将此路径交给 Lead；真实模块仍由原角色目录负责。

| 接口 | 调用输入 | 返回与失败 |
| --- | --- | --- |
| DocumentContextProvider.import_document / resolve | 上传文档句柄、current_slide、selected_text | DocumentContext；原文件只读，错误 Slide/选区/坏文件明确失败 |
| GitHubSourceVerifier.verify | 用户指定仓库、ref_or_commit、file_path、symbol、授权 | VerifiedSource（GitHubCodeSource、原请求、SOURCE_CHECKS）；未知仓库/Ref/符号/许可不能伪核验 |
| GroundedTutorProvider.explain | DocumentContext、GitHubCodeSource、question、explanation_level | GroundedExplanation；来源不足、配置缺失或无支持断言明确返回 |
| NoteStore.save | 服务端解释 ID/快照、title、user_text、显式 save_requested_by_user | SavedNote；保存时复制来源，不接受客户端替换来源 |
| VerticalSliceService.explain | 文档句柄/Slide/选区、指定代码输入、问题、级别 | 按文档→核验→Tutor 串联，返回解释句柄，尚不自动保存 |
| VerticalSliceService.save_note | 已生成解释句柄与显式保存请求 | 验证已完成可信解释后写一条笔记，数据库失败不返回成功 |

拆成 explain 与 save_note 两个用户动作：提问不创建个人笔记；任一上游失败不继续后续 Provider；save_note 失败不能回报完整闭环成功。传给下游和存储的是深拷贝/不可变快照，不能共享可变引用。

## 已注册的 API 接缝

现有 /api/demo/session、/api/learning/explain、/api/notes 与未实现的 search/verify 保持 Phase 0.5 行为。新增版本路由注册在前端静态文件挂载之前；当前 UI 继续旧路径，不在本 PR 实现上传界面。

| 接缝 | 当前实现与所有者 |
| --- | --- |
| GET /api/sprint-1/session | Provider 选择、真实能力 false、完整 fixture_example；Lead |
| POST /api/sprint-1/documents | HTTP 501，等待 Document 实现 PPTX 上传及句柄管理 |
| GET /api/sprint-1/documents/{document_id}/slides/{slide} | HTTP 501，等待 Document 实现真实 Slide |
| POST /api/sprint-1/documents/context | DocumentSelection → Provider.resolve → 校验后 DocumentContext；默认合成页 |
| POST /api/sprint-1/github/verify | SourceRequest → verifier → 服务端回执检查 → GitHubCodeSource；默认只有固定快照 |
| POST /api/sprint-1/learning/explain | question、explanation_level、document、source → 三个 Provider → 服务端解释快照 |
| POST /api/sprint-1/notes | ID、title、user_text、save_requested_by_user=true → 新版本不可变 SavedNote |
| GET /api/sprint-1/notes | 读取 Sprint 版本记录；历史记录仍在 /api/notes 原路径 |

ExplainRequest.document 使用 document_id/current_slide/current_page/selected_text，不接受客户端提供文档正文、hash 或完整 DocumentContext。ExplainRequest.source 使用 repository_url/ref_or_commit/file_path/可选 symbol/network_authorized；每次解释重新调用 verifier，不接受客户端提供 verification_status、来源快照或核验回执。SourceRequest 和返回元数据是两种不同对象，不能互换。网络授权为显式布尔值，默认 false。

可从 GET session 取得完整 fixture_example，以原样 POST explain，再用返回 grounded_explanation_id 显式 POST notes；新测试通过 TestClient 执行整条路径。原 /api/github/search 继续 NOT_IMPLEMENTED；本期不实现搜索。

## Provider 配置与失败门禁

ProviderConfig 已实现有限值校验和工厂。默认三个 Fixture Adapter 可运行；真实值只选择明确失败的预留实现，设置变量不会接通真实能力。配置从进程环境读取，.env.example 只作样例，不会自动加载。

| 场景 | DOCUMENT_PROVIDER | GITHUB_SOURCE_PROVIDER | TUTOR_PROVIDER |
| --- | --- | --- | --- |
| 默认开发与 CI | fixture | fixture | fixture |
| 真实文档/代码接缝联调 | pptx | github | fixture |
| 真实本地模型联调 | pptx | github | openai_compatible |

工厂必须校验有限值；未知值启动失败 INVALID_PROVIDER；选择尚未实现的真实 Provider 返回 PROVIDER_NOT_IMPLEMENTED。选择 openai_compatible 但未给 TUTOR_BASE_URL/TUTOR_MODEL 时返回 PROVIDER_NOT_CONFIGURED；不能自动尝试云 URL、读取无关凭据或付费回退。仅在用户明确授权指定外网仓库时运行 github Provider；CI 禁止联网。

session 保留三个 Provider 的选择，DocumentContext/GitHubCodeSource 保留各自 mode，解释保留 provider_mode。当前 FixtureGroundedTutor 只支持已有 DI 讲义/冻结源码，不能用它替换任意真实数据；Tutor 角色负责后续联合数据的固定讲解/模型适配。只要讲解使用固定文本，provider_mode 必须是 fixture，界面显示“固定讲解”；真实 PPTX + 真实 GitHub + 固定 Tutor 可以验证数据接缝，但不宣称真实模型已完成。只有实际配置且调用成功的模型能标 openai_compatible，并记录所用 endpoint 的非敏感身份、模型名和失败/未支持断言。

| 失败 | 代码（真实模块部分为待实现协议） | 必须保持的行为 |
| --- | --- | --- |
| 错误配置/未实现 Provider | INVALID_PROVIDER / PROVIDER_NOT_IMPLEMENTED | 启动或请求失败，不降级假成功 |
| 坏 PPTX/无可见文字/Slide 越界/选区不符 | INVALID_DOCUMENT / NO_VISIBLE_TEXT / INVALID_SLIDE / SELECTION_MISMATCH | 不调用来源/Tutor，不保存笔记 |
| 无联网授权/私有来源/Ref 或路径不存在/限流 | NETWORK_NOT_AUTHORIZED / SOURCE_REJECTED / SOURCE_NOT_FOUND / SOURCE_RATE_LIMITED | 不返回 Verified，显示实际原因 |
| 符号/行号/hash/许可不足 | SOURCE_UNVERIFIED / LICENSE_UNCONFIRMED | 不给“真实代码依据完成”状态；不足项显式保留 |
| 模型无配置/不可达/超时/响应违法 | PROVIDER_NOT_CONFIGURED / PROVIDER_UNAVAILABLE / PROVIDER_TIMEOUT / INVALID_PROVIDER_RESPONSE | 不切云、不静默改 Fixture |
| 引文或断言无支持 | GROUNDING_INCOMPLETE | unsupported_claims/unresolved_items 可见，不以完整有依据回答交付 |
| 未显式保存/解释不存在/存储失败 | EXPLICIT_SAVE_REQUIRED / EXPLANATION_NOT_FOUND / EXPLANATION_SAVE_FAILED / NOTE_SAVE_FAILED / NOTE_READ_FAILED | 无虚假成功，不改旧笔记 |

## 测试矩阵

| 编号 | 要验证的行为 | 主责 |
| --- | --- | --- |
| C01 | 新合同逐个删除必需字段均失败 | Lead |
| C02 | 格式正确但不匹配的 hash/行区间/选区归属失败 | Lead + Document/GitHub |
| C03 | 未核验来源改个状态标签不能进入可信服务路径 | Lead + GitHub |
| C04 | 缺运行证据不能成为 VERIFIED_RUNNABLE | Lead |
| C05 | 旧 v0.2 Fixture/笔记可读，新旧嵌套合同一致 | Lead |
| D01—D04 | 多页、空页、坏 PPTX、Slide 越界/跨页选区、原字节 hash 不变 | Document |
| G01—G04 | 固定 SHA/AST/许可正常；404/错误 Ref/符号/行号；限流；未授权不联网 | GitHub |
| T01—T04 | 两档解释；双引用；不支持断言；无配置/超时/坏响应无云回退 | Tutor |
| N01—N03 | 显式保存；保存后修改文档/仓库/内存对象不改旧快照；进程重启后同一记录 | Lead |
| E01—E04 | 全 Fixture 壳；各阶段注入失败下游不执行；真实 PPTX/GitHub + Fixture Tutor；显式启用真实模型 | Lead |
| UI01—UI03 | 上传/当前 Slide/选区；错误状态；用户文字与刷新读取笔记 | Document |

已实现 C01—C05、Fixture 输入检查、存储快照/进程重启、全 Fixture API 与各阶段失败门禁；新增 115 个测试用例。D/G/T 的真实模块与 UI 验收仍等待各角色 PR，E 的真实混合链尚未执行。

测试用临时 C2C_DATA_DIR，禁止碰现有个人笔记。Mock 的通过只证明逻辑测试；真实公网验收单独 opt-in，记录仓库/SHA/行/许可与时间，不在默认 CI 执行。测试 ID 是计划标识，不能把矩阵行数当实际新增通过数。

## 合并顺序

0. PR #56 由非作者正式 APPROVED，必需 CI 成功，正常合并；创建 pre-rules-v0.2.0，保留 v0.1。
1. Lead 在 feat/sprint-1-integration-contracts 提交“合同准备 PR”（主 Issue #5），由他人审核并正常合并；本轮不抢做真实模块。
2. Document PR 与 GitHub Verification PR 基于共同合同并行，分别解决 #7 与 #46。
3. Tutor 可以先使用 Fixture 合同并行开发；实际联合验收等待 Document/GitHub PR。
4. 最终再提交独立的 Lead 集成 PR，落实 #52。它不同于前置合同准备 PR，不能在当前合同 PR 中把所有模块都做完。

每条分支和 PR 只解决一个聚焦问题；相关任务引用不代表全部自动关闭。负责人不能批准或自动合并自己的 Sprint PR；main 保护始终不降低。

## 14 项纵向验收

- [ ] 真实 PPTX 可上传；原文件 hash 不变。
- [ ] 当前 Slide 真实可读。
- [ ] 用户选区形成合法 DocumentContext。
- [ ] 用户明确指定一个公开 GitHub 仓库。
- [ ] 来源固定到完整 Commit SHA。
- [ ] 文件与 Python 符号真实存在。
- [ ] 行号准确，片段 hash 与内容一致。
- [ ] 许可证已记录并遵守最小引用。
- [ ] 讲解同时引用 PPT 与代码；模型模式与证据一致。
- [ ] 用户主动保存个人笔记。
- [ ] 刷新及后端进程重启后仍可读取。
- [ ] 来源变化不会静默改写旧笔记。
- [ ] 所有失败状态准确，上游失败无假成功。
- [ ] Python 与前端检查实际通过，真实/Fixture 测试分开报告。

## DGX 的位置

本期关键是输入合同、核验链和不可变笔记，不依赖 DGX 部署。TUTOR_PROVIDER 的 OpenAI-compatible 接缝是后续 DGX 接入点；以后在明确授权的 endpoint/model 上接入，不改 Document/GitHub/Note 合同，不自动变更云服务或下载模型。本期 DGX 状态为 NOT_ATTEMPTED。

实现参考：FastAPI [APIRouter 官方文档](https://fastapi.tiangolo.com/tutorial/bigger-applications/)。未为此升级框架或变更 CI。
