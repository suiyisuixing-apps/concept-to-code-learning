# full-delivery-v1 · 已发布接缝

本分支是基于未合并合同的集成候选，不能称为 main。共享字段由
`src/concept_to_code_learning/full_contracts/models.py` 唯一定义；生成物在
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
SourceQuery 在这些字段上加 query_id、question、concept_terms、mode/status/revision/version。

公共检索接口：`POST /sources/search` 接受 session_id、context_revision、question、concept_terms、scope。
中央教学调用将 Tutor 概念词与用户 scope 重建成 SourceQuery；忽略模型自带的仓库/联网权限。
发送给 SourceProvider 的 question 仅由概念词组成，整页文档和问题原文不会进入来源客户端。
specified_public 必须联网已授权且 allowlist 非空；不得扩大到全网。
public_search 必须联网授权、query_terms_approved=true，且所有发送词属于 approved_query_terms；否则未调用 SourceProvider。
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
本地 dirty=true 必须 file_sha256 且 permalink=null；无已核验公开 remote 不生成网页副本链接。
许可链接固定相同 commit。相关性单独记录，来源存在/AST有效不自动证明教学相关性。

来源以 session/source_id 存储，绑定 query、scope hash、document epoch、内容 hash。source_id 不得复用不同内容或检索。
`GET /sources/{id}?session_id=...` 重新检查绑定和哈希。新请求缩小/改变授权范围需要重新检索；本地句柄撤销后不可在新讲解中继续使用。
来源 Provider 负责检索缓存/限流等模块策略；中央 SQLite registry 是当前会话的证据副本，不表示本次又联网抓取。

## 两阶段 Tutor 和追问/比较

`plan(context,question,level,conversation)` 返回 TeachingPlan。
`explain(context,verified_sources,plan,conversation,compare=False)` 返回 GroundedExplanation。
四档：Beginner / University / Engineering / Source-code，大小写固定。
上下文、问题、等级不得被 Provider 改写。输出用 block_id/source_id；任意网址由服务端拒绝，地址由来源元数据渲染。
文档 quote 必须属于相应块并符合 quote_sha256。原码和改编/生成示例必须分开；源码未执行不能声明实际运行成功。
unsupported_claims 非空、引用不存在、符号改变、原码被改写不会被悄悄删除后标成功。

追问传 continue_from=当前context下已有explanation_id；最多最近六次对话传入Tutor。
默认复用之前的核验来源版本，不自动刷新到最新 commit。显式 source_ids 必须属于当前 registry 和相同授权范围。
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

## 错误与状态

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
