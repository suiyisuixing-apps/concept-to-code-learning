# full-delivery-v1 · 已发布接缝

本分支是基于未合并合同的集成候选，不能称为 main。共享字段由
`src/concept_to_code_learning/full_contracts/models.py` 定义，独立批注合同在同目录 `annotations.py`；生成物在
`schemas/full-delivery-v1/` 和本目录 `openapi.json`。运行时 `/openapi.json` 是实际路由说明。
`python scripts/export_full_contracts.py --check` 检测声明漂移。

JSON Schema/OpenAPI检查字段形状；选区归属、内容hash、来源核验、会话授权、幂等和跨字段状态另由服务端验证。
通过 Schema 不会获得 VERIFIED 身份。新增字段需要 Lead 协调，不能在严格 Sprint 1 Schema 中直接扩展。

## 模块装配和文件所有权

| 角色 | 工厂入口 | 协议 |
|---|---|---|
| inogi | `concept_to_code_learning.documents.full.build_provider(settings)` | DocumentProvider |
| zch | `concept_to_code_learning.github_intelligence.full.build_provider(settings)` | SourceProvider |
| fqf | `concept_to_code_learning.tutor.full.build_provider(settings)` | TutorProvider |

三个 Protocol 与 `ProviderSettings` 分别在 `full_learning/ports.py`、`providers.py`。
工厂是同步的本地构造函数，返回方法为 async 的 Provider。`capabilities()` 做有界健康检查，`close()` 释放客户端。
模块在自己的目录实现，不同时改 root `api.py`、`integration/service.py`、`full_contracts`、`full_learning`。
Lead 的路由已经代理标准操作，成员一般只需交 Provider；确需额外 APIRouter 时由 Lead 检查路径冲突后挂载。
禁止 HTTP 请求指定 Python 模块/工厂或本机路径。未安装、依赖缺失、构造失败分别报告，不注册生产 Fixture 回退。

## 请求与导航

1. `POST /api/learning/v1/documents?file_name=...`，body 为真实二进制，Content-Type 为 application/octet-stream；文件名是显示名，使用 URL query 编码；最大 20 MiB。无 multipart 依赖。
2. `GET /documents`、`GET /documents/{id}/units`、`GET /documents/{id}/units/{unit_id}`；文档字段见 DTO。PDF=真实物理page，PPTX=slide，DOCX/Markdown=section。空白页保留空文本状态。
3. `POST /sessions` 得到随机 session_id 和 context_revision=0。它是本地单用户应用的会话能力标识，不是多租户身份系统；不要公开日志中的会话标识。
4. `POST /sessions/{session_id}/context` 提交 document_id、document_revision、unit_id、expected_context_revision 和可选选区；用返回的 context_revision 提问。
5. `POST /explanations` 提交 request_id、session_id、context_revision、question、level、scope。未要求 file_path/symbol。服务端再次核对实际文档版本后冻结当前请求。
6. 导航只更新 context；请求中途翻页/切文件会取消旧 generation，旧回答不可提交。并发导航用 expected_context_revision 比较更新，冲突 409 时读取最新 session 后仅重试用户最后一次动作。前端也按 request_id/context_revision 丢弃迟到结果。
7. `DELETE /requests/{request_id}?session_id=...` 取消；取消不会创建讲解或笔记。生成已完成时返回冲突，不能把保存过的笔记当作可取消临时数据。

选区：`selection_locator.spans=[{block_id,start,end}]`，end exclusive，按阅读顺序、不重叠。
位置单位为 Unicode code point；JavaScript UTF-16 offset 必须转换，尤其 emoji。
默认 exact；whitespace-v1 仅比较折叠空白后的字符串，结果仍保留服务端原文和原文 SHA256。
多块用一个换行拼接；重复文本无 locator 或不能唯一匹配时拒绝，不选第一个碰巧匹配的位置。
`POST /documents/{id}/context` 可单独预览核对，不自动改变会话。

## 来源检索、授权和注册表

`SourceScope`：source_mode，repository_allowlist（owner/repo），local_handle，language_hint，
scope_limit（默认 repositories=5/files=10），network_authorized，query_terms_approved，
approved_query_terms（精确批准的必要概念词数组），max_sources（1–3）。
SourceQuery 在这些字段上加 query_id、question、concept_terms、mode/status/revision/version，以及默认为空的 repository_hints/file_hints。

公共检索接口：`POST /sources/search` 接受 session_id、context_revision、question、concept_terms、scope。
中央教学调用将 Tutor 概念词与用户 scope 重建成 SourceQuery；忽略模型自带的仓库/联网权限。
发送给 SourceProvider 的 question 仅由概念词组成，整页文档和问题原文不会进入来源客户端。
specified_public 必须联网已授权且 allowlist 非空；不得扩大到全网。
public_search 必须联网授权。手动检索要求 query_terms_approved=true，且所有发送词属于 approved_query_terms；auto_public_search=true 时由模型提炼简短公共技术概念，中央服务校验后构造批准词集合。没有固定知识点白名单。模型建议只在已授权的自动公开搜索中作为待核验线索，不能扩大指定仓库或本地范围。

模型规划内部可返回 learning_goal，将普通追问结合材料补全成具体学习任务。它只用于本次生成，不改变公共 TeachingPlan/GroundedExplanation 的原始 question，不影响来源授权。讲解输入同时保留原始问题及补全后的目标；模型未返回目标时继续使用原问题。
local_authorized 不允许 network_authorized=true，只接受 SourceProvider 当前 local_handles() 返回的已授权句柄。
目录授权由主机进程的成员模块配置完成；本版没有任意 Web 路径注册入口。

SearchResult 的 candidates 有 query_id 与 source_mode 绑定，明确 CANDIDATE。
selection_required=true 时 `/explanations` 返回 NEEDS_SOURCE_SELECTION、query_id、candidates，explanation=null。
用户选择后用同 session/context/scope、新 request_id、query_id 和 candidate_ids 再提问，最多 max_sources 个。
高级指定路径核验仍保留旧 `/api/sprint-1/github/verify`；旧路径接口不自动升级新 registry 身份。

`POST /sources/verify` 只接受 session_id/query_id/candidate_id，不接受 CodeEvidence 或 verified=true。
SourceProvider 返回进程内 VerificationReceipt(query_id,candidate_id,scope_sha256,evidence)。
scope_sha256 是 canonical JSON SourceScope 的 UTF-8 SHA256，由 Lead 传入并核对。
来源检查项：file、line_range、excerpt_hash、license、scope；有 commit 时加 commit；公开模式加 public_repository；
上述必需项为 PASSED。Python 指定 symbol 的 python_symbol=PASSED，其他语言或无符号为 NOT_APPLICABLE。
来源仅 SOURCE_EXACT/NOT_RUN；代码行区间是 inclusive，片段哈希使用原始 UTF-8 文本，不 strip、不加注释。
许可未明确时 metadata 可保留但 code_excerpt 为空、code_display_allowed=false，不进入教学代码证据。
`ExplanationResult.source_observations` 保留最多三条未被采用的核验观察（包括许可未知的无代码元数据）；不能当作已引用来源。笔记保存这些观察的原版本，但 `code_source_ids` 仍仅表示实际教学引用。
本地 dirty=true 必须 file_sha256 且 permalink=null；无已核验公开 remote 不生成网页副本链接。
许可链接固定相同 commit。相关性单独记录，来源存在/AST有效不自动证明教学相关性。

来源以 session/source_id 存储，绑定 query、scope hash、document epoch、内容 hash。source_id 不得复用不同内容或检索。
本地句柄在检索、候选核验、复用来源时分别检查当前授权；撤销后，之前发现的候选不能继续调用核验器。
模型生成的回答正文、标题、概念说明、示例说明、比较和限制不得包含任意网址；原文引用仍须逐字匹配服务端块，代码链接统一由来源元数据渲染。
模块返回结构违反响应模型时统一返回 `INVALID_PROVIDER_RESPONSE`，不回显原返回值、Token 或主机路径。
`GET /sources/{id}?session_id=...` 重新检查绑定和哈希。新请求缩小/改变授权范围需要重新检索；本地句柄撤销后不可在新讲解中继续使用。
来源 Provider 负责检索缓存/限流等模块策略；中央 SQLite registry 是当前会话的证据副本，不表示本次又联网抓取。

## 两阶段 Tutor 和追问/比较

`plan(context,question,level,conversation)` 返回 TeachingPlan。
`explain(context,verified_sources,plan,conversation,compare=False)` 返回 GroundedExplanation。
四档：Beginner / University / Engineering / Source-code，大小写固定。
上下文、问题、等级不得被 Provider 改写。输出用 block_id/source_id；任意网址由服务端拒绝，地址由来源元数据渲染。
文档 quote 必须属于相应块并符合 quote_sha256。原码和改编/生成示例必须分开；源码未执行不能声明实际运行成功。
unsupported_claims 非空、引用不存在、原码被改写不会被悄悄删除后标成功。最终链接中的 symbol 由服务端已核验来源填写，模型只负责选择已有 source_id，不负责复制可信元数据。

追问传 continue_from=当前context下已有explanation_id；最多最近六次对话传入Tutor。
未传 continue_from 时仍提取同一文档版本最近六次已完成讲解的问答上下文，划选/翻页不清空这段会话语义；不跨文档版本，也不沿用旧选区的 source_id。真实模型将历史裁剪到最近三次。
同主题、同授权范围默认复用之前的核验来源版本，不自动刷新到最新 commit；识别出主题切换或范围变化时重新检索。显式 source_ids 必须属于当前 registry 和相同授权范围。
compare=true 需要两个不同仓库的独立证据，Comparison.source_ids 必须属于本次 code_source_ids。
无相关代码可返回只有文档依据的讲解，warnings=NO_VERIFIED_CODE；真实 Tutor 的 status=NO_VERIFIED_CODE。
授权错误、网络失败和引用完整性失败不静默降级；错误保持可见。

mode 来源于每个实际模块。任一 Fixture 依赖使回答保持 FIXTURE；所有真实模块可用仅代表 READY_FOR_LIVE_CHECK，不能自动认证产品/硬件/人工验收。
token_source=PROVIDER_USAGE 仅用于端点实际usage；估算 ESTIMATE；不可得 UNAVAILABLE 且 counts=null。时间统一UTC带时区。

## 笔记和旧数据

新数据库为 data/local/learning-v1.sqlite3（可用 C2C_DATA_DIR 换目录），旧 fixture-notes.sqlite3 和 Sprint1表不迁移、不改写。
GET /notes/legacy 原样只读投影旧两版笔记；不为旧来源补造新的 VERIFIED。
新 notes POST 要求 session_id、explanation_id、idempotency_key、save_requested_by_user=true、title、user_text。
快照在服务端事务内从已完成讲解读取，客户端不能上传替代的来源。
同幂等键同请求返回原保存结果；内容不同409。删除留下不含正文的幂等墓碑，迟到重试不重建已删笔记。
PATCH /notes/{id} 用 expected_revision 创建新用户文字修订，引用快照不变；旧修订 GET ?revision=N。
GET /notes?q=...&offset=0&limit=50 搜索当前用户标题/文字；最大100。
DELETE /notes/{id} 要求 confirmed_by_user=true 和 expected_revision，只删本应用笔记/修订副本。
GET /notes/{id}/export?format=markdown|json 使用冻结快照，网络/原文件缺失仍可读。
删除笔记不会删除原文件、来源仓库或别的会话记录；应用备份含历史讲解，应按个人数据保管。

## 本地原文批注（2026-09-11 增量）

用户要求划选原文、引用提问并保存批注；本增量增加五个独立 Schema，不改现有 ContextRequest、Note 或 Sprint 1 字段。
批注存于与 learning-v1.sqlite3 同目录的 `annotations-v1.sqlite3`，不迁移旧数据库。备份整个数据目录时一并保留此文件。

- `POST /documents/{id}/annotations`：CreateAnnotationRequest = ContextRequest + annotation_id + comment。服务端重新读取文档与单元，核对版本、选区位置、原文和 hash；从真实 DocumentContext 冻结 AnnotationAnchor。无 AI、来源检索或讲解会话依赖。
- `GET /documents/{id}/annotations?unit_id=...&offset=0&limit=50`：返回 AnnotationList，limit 最大 100；不传 unit_id 可读取整份文档批注。原文不可用时仍可读取已保存的引用。
- `PATCH /annotations/{id}`：EditAnnotationRequest 只接受 expected_revision 和 comment；原文锚点不可编辑，成功递增 revision，旧版本更新返回 409。
- `DELETE /annotations/{id}`：沿用 DeleteNoteRequest 的 expected_revision、confirmed_by_user，只删除该条批注。保留不含原文和评论的 ID 墓碑，迟到重试不会复活已删除内容。

同 annotation_id、同创建请求的重试返回已保存记录；不同内容返回 409。注释正文非空且最多 20,000 字符，原文选区最多 10,000 字符、50 个 span。编辑和删除均在 SQLite 事务内核对修订。

前端选区位置统一转为 Unicode code point。PDF.js 文字层只是选择入口；归一化仅用于找到唯一原文位置，最终提交仍为服务端块的 exact 字节文本。模糊或无法定位的 PDF 选区要求在提取文字中选择，不猜测重复文本位置。表格提供整体选择，扫描页不新增 OCR。

批注和学习笔记分别保存；改写问题或批注不会写回导入文件。现有 Host/Origin 校验与统一错误处理继续覆盖这些接口。功能与兼容性验证见 [划选与批注](../delivery/lead/SELECTION_ANNOTATIONS.md)。

## 错误与状态

### 2026-09-11 对话修复的兼容增量

本轮用户要求修复搜索失败、选择模型并简化对话，Lead 在原集成分支增加以下默认可省略字段；旧 Sprint 1 合同、原 `/explanations` JSON 路由和数据库结构保留。

- `SourceScope.auto_public_search=false`：显式启用且没有手动搜索词时，由模型从问题、选区、周围段落和同文档历史生成公共技术概念。仍要求 `network_authorized=true`。关闭此字段时，scope hash 沿用旧序列化方式，旧来源可继续核对。手动批准的空数组返回 `QUERY_TERMS_NOT_APPROVED`，不再误报模型输出错误。
- `ExplanationRequest.model_id`、`model_base_url` 默认为 null。`GET /models` 和 `POST /models/discover` 返回服务实际提供的模型；新增地址仅限本机，无用户凭据传输给新服务。每次请求绑定同一个 Tutor 做计划和回答，并在最终响应核对模型身份。
- `POST /explanations/stream` 输出 NDJSON：`progress`、`preview`、`result`、`error`。preview 只含暂时的回答正文，不构成已核验来源、已保存回答或笔记；完整 JSON 和所有引用通过校验后才输出 result。错误和断开连接取消临时生成。请求和完成结果与原 JSON 接口相同。
- `GET /sessions/recent` 返回最近有文档上下文的会话；`GET /sessions/{id}/history` 返回该本地会话最近 20 条完成讲解。不会把失败/取消请求呈现为完成回答，也不改写旧记录。

每个问题都经过模型规划。小型检索指引仅用于优先定位常见教学示例，不决定主题能否检索。AI 的 repository_hints/file_hints 默认可省略，必须在真实公开仓库和文件树中存在；过期建议、过大的自动候选树可继续查找其他公开候选。指定仓库不会静默扩大范围。

`TeachingPlan.reuse_previous_sources` 默认为 null 以兼容旧 Provider；真实模型明确判断是否延续已有代码。false 触发新检索，不能覆盖用户显式选定的 source_ids。上述增量不改变 SourceScope 哈希或数据库布局。

固定 commit 的公开 HTTP 响应可缓存24小时/48 MiB/128条，客户端重新核实公开可读后才用磁盘缓存；元数据仅在当前进程短时缓存。哈希、片段和许可检查保持不变；缓存命中不是一次新的网络读取。GitHub core/search 主配额分别退避，次级限流全局退避，不切换身份或绕过上限。

模型返回格式或引用失败时，在同一冻结证据上最多重新生成一次，所有生成用量计入结果。模型生成精简文字、文档编号和来源说明映射，由服务端组成旧响应结构；旧嵌套模型格式仍兼容。完整 JSON 后至多8个多余闭合符号可作为包装噪声去除；不接受缺失结构、额外 JSON 对象或其他尾随内容。正文必须引用实际代码标识符，引用合法性并不等于语义正确；真实验收还需检查数据流和调用。规划阶段的不确定性不再机械附到已取得代码的最终答案。

历次验证及本次上下文检索修复分别见 [对话修复验收](../delivery/lead/CONVERSATION_REPAIR.md) 和 [上下文检索验收](../delivery/lead/CONTEXTUAL_SEARCH.md)。

统一错误：request_id、stage、code、user_message、retryable、needed_action；不回显请求输入、Token、私密路径或原始异常。
成员必须按公共 B8 提供 INVALID_FILE / FILE_TOO_LARGE / UNSUPPORTED_FORMAT / NO_EXTRACTABLE_TEXT /
SELECTION_MISMATCH / DOCUMENT_VERSION_MISMATCH / NETWORK_NOT_AUTHORIZED / AUTH_REQUIRED / RATE_LIMITED /
REPO_UNAVAILABLE / REF_UNRESOLVED / FILE_NOT_FOUND / SYMBOL_NOT_FOUND / SOURCE_MISMATCH / LICENSE_UNKNOWN /
NO_RELEVANT_SOURCE / MODEL_NOT_CONFIGURED / MODEL_UNAVAILABLE / CONTEXT_LIMIT / MODEL_OUTPUT_INVALID /
CITATION_INVALID / STORAGE_FAILURE / CANCELLED 等语义。当前未交付模块的相关真实失败路径不能假报实测。
中央另有 QUERY_TERMS_NOT_APPROVED、CONTEXT_REVISION_CONFLICT、REQUEST_CONFLICT、REVISION_CONFLICT 等明确冲突码。

官方 API 依据：[FastAPI响应模型](https://fastapi.tiangolo.com/tutorial/response-model/)、
[Pydantic JSON Schema](https://docs.pydantic.dev/latest/concepts/json_schema/)、
[Python3.12 SQLite事务与连接](https://docs.python.org/3.12/library/sqlite3.html)。
SQLite connection context仅处理事务，closing负责关闭；本实现不在数据库事务中 await。


2026-09-11 引用绑定修复：默认模型内部协议改为 `NarrativeOutput`（answer、可选 comparison/tradeoffs、limitations）。服务端在生成前固定输入包，回答的文档引用绑定实际给出的选区块或首个上下文块，源码引用绑定给出的已核验片段。模型不生成仓库身份、行范围或来源 ID。`PlainTeachingOutput` 和原 `TeachingOutput` 仍可读；凡响应声明了引用，必须通过原有逐项校验，不能删掉错误引用后降级发布。生成预览不保存，最终输出仍经过来源、范围、原始字节、引用和代码相关性检查。`GROUNDED` 不等于逐句语义正确，来源卡片表明本次输入依据。公共 DTO、已有笔记、历史回答及旧接口保持原样。
