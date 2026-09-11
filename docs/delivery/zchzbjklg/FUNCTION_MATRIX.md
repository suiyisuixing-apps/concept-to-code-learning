# 功能矩阵 — github_intelligence（@zchzbjklg）

**Issue**: #67 `[Full delivery] 三模式代码发现、检索与固定来源核验`
**基线**: `feat/full-learning-integration`
**模块**: `src/concept_to_code_learning/github_intelligence/`
**测试**: `tests/github_intelligence/`

本表描述集成基线已有生产实现。`REAL` 指真实运行的本地逻辑，HTTP 输入仍使用替身，
`LOCAL_VERIFIED` 不是实际 GitHub/模型验收。当前集成结果见 [PR73_REVIEW.md](../lead/PR73_REVIEW.md)。

状态口径（三者独立，不合并成一个布尔值）：

- `实现` = 真实代码路径存在且被测试驱动
- `真实性` = `REAL`（真实逻辑，真实字节/哈希/AST）/ `FIXTURE`（合成数据）/ `MOCK`（测试替身提供 IO）
- `实测` = `LOCAL_VERIFIED`（本机真实跑过并留证）/ `NOT_RUN` / `BLOCKED_*`

---

## C1 · 模块装配与接入

| 能力 | 实现 | 真实性 | 实测 | 位置 |
|---|---|---|---|---|
| `build_provider(settings) -> SourceProvider` | ✅ | REAL | LOCAL_VERIFIED | `full.py` |
| 构造期零网络（httpx 客户端惰性建立） | ✅ | REAL | LOCAL_VERIFIED | `full.py:32-38` |
| `capabilities()` 报告 implemented/available/features/data_flow | ✅ | REAL | LOCAL_VERIFIED | `full.py:54-74` |
| `close()` 释放连接与内存缓存 | ✅ | REAL | LOCAL_VERIFIED | `full.py:98-99` |
| 不越界改 `schemas/`、`full_learning/`、`full_contracts/`、`apps/web` | ✅ | — | — | 本 PR diff 仅动自身目录＋交付文档 |

## C2 · 三来源模式

| 能力 | 实现 | 真实性 | 实测 | 说明 |
|---|---|---|---|---|
| `specified_public` search | ✅ | REAL | LOCAL_VERIFIED | 仅 `repository_allowlist`；空 allowlist → `NO_RELEVANT_SOURCE` 422 |
| `specified_public` verify | ✅ | REAL | LOCAL_VERIFIED | `verifier.verify_specified_public` |
| `public_search` search | ✅ | REAL | LOCAL_VERIFIED | 内部需 `network_authorized` + `query_terms_approved` 且批准词覆盖 `concept_terms`；普通界面在用户授权公开搜索后由 AI 提炼词，不要求用户手填知识点，否则 `QUERY_TERMS_NOT_APPROVED` 403 |
| `public_search` verify | ✅ | REAL | LOCAL_VERIFIED | 与 specified_public 共用核验路径，但不受 allowlist 限制 |
| `local_authorized` search | ✅ | REAL | LOCAL_VERIFIED | 只读 Git 已跟踪文件；不联网（`network_authorized` 必须为 False） |
| `local_authorized` verify | ✅ | REAL | LOCAL_VERIFIED | 校验检索后文件未变更，否则 `SOURCE_MISMATCH` 409 |
| 只发批准的必要概念词，不带整页文档/私有问题原文 | ✅ | REAL | LOCAL_VERIFIED | 出站查询只由 `concept_terms` 构成；被测试断言（`test_hostile_concept_terms_cannot_break_out_of_the_quoted_search_query`；仓库注入另测） |
| 本地模式只读主机预注册句柄，不接受 web 任意路径 | ✅ | REAL | LOCAL_VERIFIED | `LocalRegistry` 仅由 `ProviderSettings.authorized_local_roots` 构造 |
| 缺失 token 只阻塞相关接口 | ✅ | REAL | NOT_RUN | 见下方「外部阻塞」 |
| 未知 `source_mode` → `INVALID_PROVIDER_RESPONSE` 422 | ✅ | REAL | LOCAL_VERIFIED | `full.py:81-92` |

### 认证与限流说明（C2 要求「精确说明」）

| GitHub API | 端点 | 认证 | 限流桶 |
|---|---|---|---|
| 仓库元数据 | `api.github.com/repos/{o}/{n}` | 匿名可读；公开仓库无需 token | core |
| ref → commit | `/repos/{o}/{n}/commits/{ref}` | 匿名可读 | core |
| 文件树 | `/repos/{o}/{n}/git/trees/{sha}?recursive=1` | 匿名可读；`truncated` 时按不完整处理 | core |
| 文件字节 | `/repos/{o}/{n}/contents/{path}?ref={sha}` | 匿名可读；返回 base64 与 blob sha | core |
| 仓库搜索 | `/search/repositories` | 匿名可用但配额低；token 显著提高配额 | search（**独立配额**） |
| raw 主机 | `raw.githubusercontent.com` | 代理解析未使用；不走它 | — |

- hosts 白名单：`{api.github.com}`。非 https、非白名单、带 userinfo 的地址一律 `NETWORK_NOT_AUTHORIZED` 403。
- `401/403` → `AUTH_REQUIRED`；`404` → `FILE_NOT_FOUND`；`403|429` 且 `x-ratelimit-remaining: 0` 或带 `retry-after` → `RATE_LIMITED` 429 并记录窗口（search/core 分桶，secondary limit 记 `all`）。
- token 只从 `ProviderSettings.github_token`（源自 `C2C_GITHUB_TOKEN`）读入，**只**附加到 `api.github.com` 请求；不进异常、日志或磁盘缓存（有测试断言持久化文件不含 token 明文）。

## C3 · 从概念发现代码

| 能力 | 实现 | 真实性 | 实测 | 说明 |
|---|---|---|---|---|
| 中英文概念词 → 文件候选 | ✅ | REAL | LOCAL_VERIFIED | `discovery.tokens` 按 camelCase 切分、复数归一 |
| 概念**整体**匹配优先于零散词 | ✅ | REAL | LOCAL_VERIFIED | `discovery.matched` 要求 `tokens(term) ⊆ tokens(text)`；避免只命中一个常见词便宣称完整概念匹配 |
| 语言提示过滤 | ✅ | REAL | LOCAL_VERIFIED | `EXTENSIONS` 覆盖 py/js/ts/go/rs/java/c/cpp/cs/rb/swift |
| 稀有词加权（IDF）+ 文件名加权 | ✅ | REAL | LOCAL_VERIFIED | `ranked_paths` |
| Python 符号定位（AST，仅静态） | ✅ | REAL | LOCAL_VERIFIED | `python_symbols`；`ast.parse` 失败则退化为文本模式 |
| 相关测试文件识别 | ✅ | REAL | LOCAL_VERIFIED | 排序时将 `tests/` 目录降权 |
| 有界配额：默认 ≤5 仓库 / ≤10 文件 / 解释 ≤3 片段，可配置 | ✅ | REAL | LOCAL_VERIFIED | `ScopeLimit`(repositories≤20, files≤100)、`max_sources`(1..3) |
| `SearchCandidate` 记录匹配词/依据/检索方式/时间 | ✅ | REAL | LOCAL_VERIFIED | `discovery.candidate` |
| 不以人气或 AST 存在率等同教学相关性 | ✅ | REAL | LOCAL_VERIFIED | `relevance.status` 恒为 `CANDIDATE`/`UNCERTAIN`，理由中明写"不证明教学结论" |
| 歧义时请求用户选候选 | ⚠️ 契约就绪 | REAL | NOT_RUN | `SearchResult.selection_required` 字段可用；主动追问由 Lead 编排层触发 |
| 仓库文件树被截断时给 warning | ✅ | REAL | LOCAL_VERIFIED | `specifier.py:54-55` |

## C4 · 精确来源证据

| 能力 | 实现 | 真实性 | 实测 | 说明 |
|---|---|---|---|---|
| 先固定 commit 再读字节 | ✅ | REAL | LOCAL_VERIFIED | `fetch_raw` 拒绝非 40-hex commit → `REF_UNRESOLVED` 422 |
| ref 漂移检测（声称 40-hex 但解析到别的 commit） | ✅ | REAL | LOCAL_VERIFIED | `verifier.py:137-138` → `SOURCE_MISMATCH` 502 |
| inclusive 行号 + 原文精确 | ✅ | REAL | LOCAL_VERIFIED | `excerpt()`；尾部空行不当作额外行 |
| `excerpt_sha256` 绑定展示片段 | ✅ | REAL | LOCAL_VERIFIED | 模型校验器强制 `digest(code_excerpt) == excerpt_sha256` |
| `file_blob_sha` 与下载字节一致 | ✅ | REAL | LOCAL_VERIFIED | 本地重算 `sha1("blob <len>\0"+raw)` 比对，不符 → `SOURCE_MISMATCH` 502 |
| `file_sha256` | ✅ | REAL | LOCAL_VERIFIED | |
| Python 仅静态 AST，不 import | ✅ | REAL | LOCAL_VERIFIED | 公开源码仅用 AST；本地核验另有受限 Git 静态读取 |
| 非 Python 标 AST `NOT_APPLICABLE` | ✅ | REAL | LOCAL_VERIFIED | |
| 不可变 permalink `blob/<sha>/<path>#Lx-Ly` | ✅ | REAL | LOCAL_VERIFIED | |
| 许可从相同 commit 读取 | ✅ | REAL | LOCAL_VERIFIED | `_resolve_license` 用同一 `commit` 取树 |
| `DETECTED / UNKNOWN / MIXED` + 适用限制 | ✅ | REAL | LOCAL_VERIFIED | `license_observation` |
| 未知/混合许可默认保留元数据但不展示原码 | ✅ | REAL | LOCAL_VERIFIED | `code_display_allowed=False` → `code_excerpt=""`、`NEEDS_CONFIRMATION` |
| 不猜 MIT | ✅ | REAL | LOCAL_VERIFIED | `detect_identifier` 只认明确标题/条款特征 |
| 树截断时强制 UNKNOWN 并附限制说明 | ✅ | REAL | LOCAL_VERIFIED | `verifier.py:223-226` |
| 不执行第三方代码/Notebook/install 脚本 | ✅ | REAL | LOCAL_VERIFIED | 不执行来源源码；本地模式有受限 Git 静态读取子进程 |
| Notebook cell 定位 | ❌ 未支持 | — | — | 本切片不声明 Notebook 能力 |

## C5 · 本地与来源注册表

| 能力 | 实现 | 真实性 | 实测 | 说明 |
|---|---|---|---|---|
| 只注册主机预授权句柄（opaque handle，不含路径） | ✅ | REAL | LOCAL_VERIFIED | `handle = "local-" + sha256(root)[:24]` |
| 拒绝 `..` / 绝对路径 / 反斜杠 / NUL | ✅ | REAL | LOCAL_VERIFIED | `rejects_escape` |
| 拒绝越界 symlink（逐段 + `O_NOFOLLOW`） | ✅ | REAL | LOCAL_VERIFIED | `registry.read` |
| 拒绝非普通文件（设备/目录）与 >1 MiB | ✅ | REAL | LOCAL_VERIFIED | `stat.S_ISREG` |
| 拒绝越过 Git root | ✅ | REAL | LOCAL_VERIFIED | 句柄即 Git 仓库根，读取按相对路径 |
| 授权根被替换检测（dev/ino 复核） | ✅ | REAL | LOCAL_VERIFIED | `_identities` |
| dirty=true + 文件哈希 | ✅ | REAL | LOCAL_VERIFIED | 与 `git show HEAD:<path>` 字节比对 |
| 无公开 remote 不伪造 GitHub URL | ✅ | REAL | LOCAL_VERIFIED | local 证据 `permalink=None`、`repository_url=None` |
| `VerificationReceipt(query_id, candidate_id, scope_sha256, evidence)` | ✅ | REAL | LOCAL_VERIFIED | |
| 来源 ID 不可变、取回不重定向最新分支 | ✅ | REAL | LOCAL_VERIFIED | `source_id = candidate_id`；读取一律带固定 commit |
| 客户端 `verified=true` 不作为凭证 | ✅ | REAL | LOCAL_VERIFIED | 不存在接受客户端回执的入口 |

## C6 · 客户端、缓存与失败处理

| 能力 | 实现 | 真实性 | 实测 | 说明 |
|---|---|---|---|---|
| HTTPS 校验 + 不跟随跨主机重定向 | ✅ | REAL | LOCAL_VERIFIED | `follow_redirects=False`；`trust_env=False` |
| 只调用允许的 GitHub 域名/接口 | ✅ | REAL | LOCAL_VERIFIED | `ALLOWED_HOSTS` 白名单 |
| 有限超时（≤30s） | ✅ | REAL | LOCAL_VERIFIED | `asyncio.timeout` |
| 有限重试（≤1 次） | ✅ | REAL | LOCAL_VERIFIED | `min(1, max(0, retries))` |
| 响应体上限（树 8 MiB / 内容 2 MiB / 其他 1 MiB） | ✅ | REAL | LOCAL_VERIFIED | 流式累计超限即 `INVALID_PROVIDER_RESPONSE` 413 |
| `401/403/404/429` 与 rate headers 识别 | ✅ | REAL | LOCAL_VERIFIED | `_interpret` |
| 尊重重试时间但不无限等待 | ✅ | REAL | LOCAL_VERIFIED | 记窗口后立即返回 429，最长记 3600s |
| search/core 独立配额；secondary limit 全局 | ✅ | REAL | LOCAL_VERIFIED | 分桶 `search`/`core`/`all` |
| token 不进浏览器/异常/日志 | ✅ | REAL | LOCAL_VERIFIED | 有断言：持久化缓存文件不含 token |
| 持久缓存按 repo/commit/file 绑定（URL 含固定 sha） | ✅ | REAL | LOCAL_VERIFIED | 仅 `immutable` URL 才落盘 |
| 持久缓存有限容量 + 过期 + 校验和 + 原子写 | ✅ | REAL | LOCAL_VERIFIED | 48 MiB / 128 项 / 24h；`os.replace` |
| 复用磁盘字节前重新确认仓库仍公开 | ✅ | REAL | LOCAL_VERIFIED | `_public_repositories` |
| 缓存损坏/过期/删除后不回退别的仓库 | ✅ | REAL | LOCAL_VERIFIED | 取不到就重新请求，绝不替换来源 |
| 本次取证时间与联网证据分开 | ✅ | REAL | LOCAL_VERIFIED | `retrieved_at` 为本次构造时间，单凭该字段不能证明重新联网；需查看实际请求/缓存记录 |
| 上下文/文档不进入公共查询 | ✅ | REAL | LOCAL_VERIFIED | 出站查询只由概念词构成 |
| 仓库内容一律视为不可信材料 | ✅ | REAL | LOCAL_VERIFIED | 有注入用例断言 |

## C7 · 测试与交付

| 要求 | 覆盖 | 位置 |
|---|---|---|
| 三模式正例 | ✅ | `test_full.py`、`test_specifier.py`、`test_product_completion.py` |
| 未授权 | ✅ | `test_full.py`、`test_verifier.py`、`test_public_cache.py` |
| 未知 repo / ref / file / symbol | ✅ | `test_verifier.py` |
| 行数 / hash 错配 | ✅ | `test_source_failure_matrix.py`、`test_product_completion.py` |
| 范围扩大（AI 提示不得扩权） | ✅ | `test_contextual_discovery.py` |
| 错误许可 | ✅ | `test_verifier.py` |
| 分页 / 截断 | ✅ | `test_source_failure_matrix.py`、`test_contextual_discovery.py` |
| 限流 | ✅ | `test_public_cache.py`、`test_source_failure_matrix.py` |
| 超时 | ✅ | `test_source_failure_matrix.py` |
| 取消 | ✅ | `test_source_failure_matrix.py` |
| 缓存隔离 | ✅ | `test_public_cache.py` |
| 恶意 README / 不可信仓库内容 | ✅ | `test_source_failure_matrix.py` |
| symlink | ✅ | `test_product_completion.py`、`test_registry.py` |
| dirty 本地路径 | ✅ | `test_product_completion.py` |
| 合成本地 Git 库真实静态读取并记录命令 | ✅ | `test_source_failure_matrix.py`、`test_product_completion.py` |
| 公开库实测（固定版本 + 最小片段 + 许可 + 时间） | 本切片未新增 | Lead 既有真实证据见 CONTEXTUAL_SEARCH.md，与本次 Mock 分开 |
| `deps/zchzbjklg.txt` + 依赖说明 | ✅ | `deps/zchzbjklg.txt` |
| HANDOFF / 五分钟检查 / 真实与 Mock 矩阵 | ✅ | 本目录 |
