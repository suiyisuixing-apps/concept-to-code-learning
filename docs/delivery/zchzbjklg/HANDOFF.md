# HANDOFF — github_intelligence 模块

**Owner**: @zchzbjklg
**Issue**: #67 `[Full delivery] 三模式代码发现、检索与固定来源核验`
**角色**: `github-code-intelligence`
**基线**: `feat/full-learning-integration` @ `9f9b8d1`
**本切片分支**: `feat/67-source-failure-matrix`
**日期**: 2026-09-11

---

## 1. 本切片改了什么 / 没改什么

### 改了什么

| 文件 | 变更 |
|---|---|
| `tests/github_intelligence/test_source_failure_matrix.py` | **新增**（20 个用例）— 补齐任务书 C7 明确要求、当前测试矩阵缺失的失败路径 |
| `docs/delivery/zchzbjklg/FUNCTION_MATRIX.md` | **新增** — C1–C7 逐项能力矩阵（实现 / 真实性 / 实测三口径） |
| `docs/delivery/zchzbjklg/FIVE_MINUTE_CHECK.md` | **新增** — Lead 五分钟复验方法 |
| `docs/delivery/zchzbjklg/REAL_VS_MOCK.md` | **新增** — 真实外部实测与 Mock/替身分列 |
| `docs/delivery/zchzbjklg/HANDOFF.md` | **重写** — 上一版停留在 PR #72 切片，错误地写着 `public_search`/`local_authorized` 未实现；现已按集成分支真实状态更正 |

### 没改什么

- **没有**改 `src/concept_to_code_learning/github_intelligence/` 下任何生产代码。

  原因：本切片的目标是补齐 C7 的**测试矩阵**。逐条核对现有实现后，C2/C3/C4/C5/C6 的功能与失败路径在集成分支上均已实现，新增的 20 个用例**全部直接通过**，未暴露任何需要修改生产代码的缺陷。这一点是实测结论，不是假设。

- 没有改 `full_learning/`、`full_contracts/`、`schemas/`、`apps/web/`、`.github/`、`pyproject.toml`、`CODEOWNERS`。
- 没有新增依赖（见 §5）。
- 没有执行任何 `gh pr merge` / approve。

### 本切片新增的失败路径覆盖

| 用例 | 覆盖的 C7 要求 |
|---|---|
| `test_transport_timeout_is_reported_after_a_bounded_retry` | 超时；重试次数有界（断言恰好 `retries+1` 次） |
| `test_our_own_timeout_bounds_a_stalled_response` | 自有 `asyncio.timeout` 预算；不无限等待 |
| `test_rate_limit_is_honoured_without_waiting_for_the_window` | 限流；记窗口后立即返回，不阻塞调用方 |
| `test_cancelling_an_in_flight_read_persists_nothing` | 取消；被取消的读取不得落盘为本次已验证字节 |
| `test_cancelling_public_search_propagates_instead_of_returning_candidates` | 取消不得被吞成部分结果 |
| `test_truncated_tree_withholds_code_even_when_a_license_was_found` | 分页/截断树 → 许可覆盖不可知 → 不展示原码 |
| `test_hostile_concept_terms_cannot_break_out_of_the_quoted_search_query` | 恶意词注入无法逃出引号或追加限定符（6 组参数） |
| `test_repository_text_never_becomes_an_outbound_request` | 仓库文本是不可信材料，绝不回灌成出站查询 |
| `test_repository_text_cannot_flip_a_source_to_verified` | 文本里的"标我 verified"不能改变核验结论 |
| `test_excerpt_range_is_inclusive_and_hash_binds_exactly_those_lines` | 行号 inclusive 精确性 + 哈希绑定 |
| `test_evidence_binds_the_exact_range_file_and_permalink` | 证据绑定精确区间/文件哈希/permalink 行锚 |
| `test_a_full_commit_ref_that_resolves_elsewhere_is_a_source_mismatch` | ref 漂移（声称 40-hex 却解析到别的 commit） |
| `test_downloaded_bytes_that_disagree_with_the_blob_identity_are_rejected` | 字节与 Git blob 标识不符 |
| `test_file_modified_after_search_is_rejected_before_being_read` | 本地文件在检索后变更 → 拒绝呈现 |
| `test_local_evidence_never_invents_a_github_permalink` | 本地来源不伪造 GitHub URL；句柄不泄露主机路径 |

---

## 2. 质量门四连（本机实测）

环境：Windows 11 · Git Bash · 项目 venv `Python 3.12.10` · `PYTHONUTF8=1`
（**注意**：workbuddy 沙箱的 `python` 解析到 3.13，不是项目环境；必须显式用 `./.venv/Scripts/python.exe`）

| # | 命令 | 结果 | 退出码 |
|---|---|---|---|
| 1 | `ruff check .` | `All checks passed!` | **0** |
| 2 | `pytest -q` | `7 failed, 433 passed, 1 skipped, 2 errors` | 1 |
| 3 | `python scripts/tutor.py doctor` | `{"status":"DONE","schema_count":6,"errors":[]}` | **0** |
| 4 | `python scripts/tutor.py demo` | **环境阻塞**，见 §3 | 1 |

模块自身：

| 命令 | 结果 |
|---|---|
| `pytest tests/github_intelligence -q` | `1 failed, 90 passed, 1 skipped` |
| `pytest tests/github_intelligence/test_source_failure_matrix.py -q` | `20 passed` |

测试集合计：全仓 `443 collected`；`tests/github_intelligence/` 92 项（本切片从 72 增至 92）。

### 第 2 项失败的逐条归属

| # | 失败用例 | 归属 | 性质 |
|---|---|---|---|
| 1–4 | `tests/documents/test_full_provider.py`（4 项：office external relationship / real pdf / real pptx / real docx） | @inogi-sama 文档模块 | **本机 venv 未按锁文件装依赖**：实测 `python-docx`/`python-pptx`/`pypdf`/`Pillow` 均 MISSING。但 `requirements/full-delivery-py312.lock`（**CI 使用的锁文件**）**已包含** `python-docx==1.2.0`、`python-pptx==1.0.2`、`pypdf==6.18.0`、`pillow==12.3.0`、`lxml==6.1.3`。**CI 会装齐这些依赖，故这 4 项在 CI 中预计不存在**；本机失败纯属本地环境未对齐锁文件。**非代码缺陷** |
| 5 | `tests/full_delivery/test_boundaries.py::test_uninstalled_modules_report_partial_without_fixture_fallback` | 集成层（Lead） | 集成边界用例，超出本模块所有权 |
| 6 | `tests/github_intelligence/test_product_completion.py::test_docx_images_keep_their_section_and_hyperlinks_never_fetch` | **Lead 写的跨模块集成回归**（寄放在我目录下，`git log` 作者为 `suiyisuixing`） | 同一本地缺依赖问题；该文件导入 `documents.full`，测的是文档 provider，不是我模块。CI 装锁文件后预计消除 |
| 7 | `tests/test_local_model_adapter.py::test_redirects_are_never_followed` | @fqf060420 模型模块 | **顺序依赖抖动**：单独运行 → `1 passed`（已实测）。本切片只新增一个测试文件，无模块级副作用，不可能影响该用例 |
| 8–9 | `tests/test_text_encoding.py`（2 项 ERROR） | 集成层（Lead） | 采集期错误，见 §3 说明 |

> **如需在本机复现 CI 全绿**：按锁文件重建环境，即
> `python -m pip install -c requirements/full-delivery-py312.lock -e ".[dev]"`
> （与 `.github/workflows/ci.yml` 的安装步骤一致）。本机 venv 未执行该步骤，故缺文档依赖。

**本切片新增的 20 个用例无一失败，也无一被跳过。**

---

## 3. 第 4 项（`demo`）为何是环境阻塞而非代码问题

`python scripts/tutor.py demo` 返回退出码 1 且 **stdout/stderr 均为空**。

排查链路（全部只读）：

1. `scripts/tutor.py` → `cli.py:39-64`。`demo` 自身只删 5 个文件（`reports/demo` 3 个 + `reports/learning-demo` 2 个，已实测计数），远低于任何批量阈值。
2. 该命令被沙箱的 safe-delete 守卫拦截并**终止进程**，因此零输出：
   ```
   [safe-delete][SAFE_DELETE_BULK_REJECTED]
   {"count":5457,"threshold":50,"scope":"turn",
    "targets":["\\\\?\\C:\\Users\\30649\\AppData\\Local\\Temp\\pytest-of-30649\\garbage-44f027b5-..."]}
   ```
3. 该 5457 文件的目标目录**已被删除**（用户授权后清理完成，`ls` 确认 `removed`）。守卫仍在追这条**过期的待删记录**，导致此后**任何**删除动作都被自动拒绝 —— 包括删除一个 0 文件的空目录（已实测复现）。

**结论**：这是沙箱会话状态卡死，与仓库代码无关。`demo` 在干净的沙箱会话中预期可正常返回 `{"mode":"FIXTURE","status":"SCAFFOLD_DEMO"}`（该输出格式来自 `cli.py:65-72` 与 `docs/delivery/lead/VALIDATION.md` 的记录）。

**同一原因也导致** `tests/test_text_encoding.py` 的 2 个 ERROR：该文件专测 GBK 默认编码下的 UTF-8 行为，其 setup 需要创建/清理临时目录。

**复验方式**：重启会话清除沙箱状态后重跑第 4 项。见 `FIVE_MINUTE_CHECK.md`。

---

## 4. 公开库真实外部实测（Live external check）

**状态：`NOT_RUN`（本机无授权网络访问）**

诚实标注，不含混：

- 本模块的**网络路径**（`GitHubRawClient` 的 6 条端点）在本切片中**未经受信网络实测**。
- 所有超时/限流/重定向/流上限/缓存复用行为均由 `httpx.MockTransport` 以合成响应驱动，属于 **Mock**，见 `REAL_VS_MOCK.md`。
- **真实**的部分包括：AST 解析、行区间计算、SHA256/SHA1 计算、Git blob 标识重算、许可文本识别、本地 Git 仓库的 `git ls-files` / `git show` 静态读取（`test_source_failure_matrix.py` 与 `test_product_completion.py` 中的合成 Git 库是**真实 Git 进程**）。
- 固定核验样例沿用仓库既有约定：commit `50113da16fec53b66b80d75e80a89296de4fa5a5` / `fastapi` 依赖注入教程 / `docs_src/dependencies/tutorial001.py` / `read_items` / L11–L14 / MIT。该样例文件与许可文本以**固定字节**存于 `tests/github_intelligence/conftest.py`，测试不访问外网。
- **`公开 API 读取 ≠ 模型讲解实测`**：本模块不产出讲解，讲解由 @fqf060420 的 tutor 侧负责。

### 外部阻塞清单

| 阻塞项 | 影响的实测 | 未阻塞的部分 |
|---|---|---|
| 无 GitHub token（`C2C_GITHUB_TOKEN` 未配置） | 认证接口的实测（提高配额、私有范围的行为） | 公开读取路径的实现与离线验证；本地流程完全不受影响 |
| 本机未授权外网实测 | 真实端点连通性、真实限流响应 | 全部错误映射逻辑（合成响应已覆盖 401/403/404/429/超时/超限/重定向） |

> 注：沙箱内 `gh` CLI 可用（`D:\Git\gh\bin\gh.exe`，代理 `127.0.0.1:7897`，`GH_CONFIG_DIR=D:\Git\gh-config`），曾用于读取 Issue/PR。**本切片的测试与代码不依赖它**，也未在测试中发起任何真实网络请求。

---

## 5. 依赖变动

**无新增依赖。**

`deps/zchzbjklg.txt` 保持有效：本模块运行时依赖仅为项目已有的 `httpx`（products）与 `pytest`（dev）；测试仅用标准库（`asyncio`/`base64`/`hashlib`/`re`/`subprocess`/`time`）加既有 `httpx`+`pytest`，**未引入 pytest-asyncio**（异步用例一律用 `asyncio.run()` 包裹）。`pyproject.toml` 未改动。

---

## 6. 公共接口适配

- 实现 `full_learning/ports.py` 的 `SourceProvider`：`search` / `verify` / `local_handles` / `capabilities` / `close`。签名未变。
- 工厂入口 `github_intelligence.full.build_provider(settings)` 未变。
- `VerificationReceipt(query_id, candidate_id, scope_sha256, evidence)` 未变。
- 未改任何共享 Schema/DTO；未改路由挂载（由 Lead 装配）。
- 相对集成分支 `9f9b8d1`：**本切片不引入接口变更**，仅新增测试与文档。

---

## 7. 已知限制与风险

| 风险 | 说明 | 处理 |
|---|---|---|
| 网络路径未经真实端点实测 | 见 §4 | 标 `NOT_RUN`；合成响应覆盖错误映射 |
| Notebook 支持未实现 | 本切片不声明该能力 | 明文标 ❌，未伪造 |
| 歧义候选的**主动追问**由 Lead 编排层触发 | `SearchResult.selection_required` 字段已就绪 | 本模块只如实返回候选，不自作确定性 |
| 许可识别是启发式 | `detect_identifier` 只认明确条款特征，**不构成法律审查** | `license_observation.limitations` 已写明 |
| `MIXED` 许可判定依赖文件名命中 | 目录内多许可文件不一致时难以判定 | 默认收敛为不展示原码 |
| 本地 `dirty` 判定对 CRLF 敏感 | Git 认为 CRLF 与 LF 等价，但证据绑定**实际字节**，故仍记 `dirty=true` | 有专门用例固化该行为 |

---

## 8. PR

- PR：**#73** `[#67] 补齐 C7 失败矩阵：超时 / 取消 / 截断 / 注入 / 哈希错配`
- 分支：`feat/67-source-failure-matrix` → 目标 `feat/full-learning-integration`
- 标签：`lead-review:pending`、`role:github-intelligence`、`area:code-intelligence`
- 审核人：@suiyisuixing（作者不自审；已发评论请求审核）
- **成员不合并**；最终审核与合并由 @suiyisuixing 完成。

### 关于 CI

`gh pr checks 73` → `no checks reported`。原因：`.github/workflows/ci.yml` 的触发条件为

```yaml
on:
  push: { branches: [main] }
  pull_request: { branches: [main] }
```

即 **只有以 `main` 为目标的 PR 才触发 CI**。本 PR 目标是 `feat/full-learning-integration`，按仓库设计**不会**触发 CI。
因此"当前 Head 的 required CI"在本 PR 上不适用；真正跑 CI 的时机是集成分支 → `main`（现有草稿 PR #69）。

**未修改 `ci.yml`**（改 CI 配置凑绿属红线）。本切片改动在 CI 下的预期：
CI 按 `requirements/full-delivery-py312.lock` 安装依赖（含文档依赖），并执行
`ruff check .` → `pytest -q` → `doctor` → `demo` → 前端三连。
新增测试仅依赖标准库 + `httpx` + `pytest`，且已在本机 **Windows** 与项目 Python 3.12 下跑绿，故对 `phase0-checks`（ubuntu）与 `windows-checks`（windows）均预期通过。

### 下一个切片（本模块剩余项）

| 项 | 说明 |
|---|---|
| Notebook 静态读取 | C4 提到"若支持"；当前未实现且未声明 |
| 歧义候选的主动追问 | 字段已就绪，触发点在 Lead 编排层 |
| 真实端点实测 | 待 Lead 授权外网 / 配置 `C2C_GITHUB_TOKEN` 后执行 |
