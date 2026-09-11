# 真实外部实测 vs Mock — github_intelligence（@zchzbjklg）

任务书 A6 要求把 `implementation` / `module_tests` / `live_external_check` /
`integrated_product` / `target_hardware` / `lead_review` **分开记录**，不能用一个绿色字段包办。

| 维度 | 状态 | 证据 |
|---|---|---|
| `implementation` | ✅ 完成（集成分支既有 + 本切片测试补齐） | `src/concept_to_code_learning/github_intelligence/` 10 个文件 |
| `module_tests` | ✅ `90 passed, 1 skipped`（+ 1 failed 属 Lead 集成回归缺 docx 依赖） | `pytest tests/github_intelligence -q` |
| `live_external_check` | ⚠️ **`NOT_RUN`** — 本机未授权外网实测 | 见下表“未实测”栏 |
| `integrated_product` | ⏳ 由 Lead 装配验收 | 本模块只提供 `SourceProvider` factory |
| `target_hardware` | — 不适用（无 DGX/硬件依赖） | — |
| `lead_review` | ⏳ 待 @suiyisuixing | PR 标 `lead-review:pending` |

---

## 1. 逐能力：真实 / 替身

| 能力 | 本次真正执行的部分（REAL） | 用替身/合成数据驱动 IO 的部分（MOCK） | 未实测（NOT_RUN） |
|---|---|---|---|
| `specified_public` 检索 | 排序算法、概念词匹配、语言过滤、配额裁剪——真实代码路径 | 文件树与文件字节由 `FakeGitHubRawClient` 返回固定字节 | 真实 GitHub tree/contents 端点 |
| `public_search` 检索 | 授权门控（`network_authorized` + 逐词批准）、AI 提示不得扩权、查询词净化 | 仓库搜索结果由替身返回 | `/search/repositories` 真实调用与真实配额 |
| `local_authorized` 检索 | **真实**：真实 Git 进程 `git ls-files`、真实文件读取、真实 SHA256 | — | 无（本地路径无需外网） |
| 固定 commit 核验 | Python **真实 `ast.parse`**、真实行区间计算、真实 SHA256 | 文件字节由替身提供 | 真实 40-hex commit 解析 |
| `file_blob_sha` 校验 | **真实**：本地按 `sha1("blob <len>\0"+raw)` 重算并与远端值比对 | 远端 blob sha 由替身提供 | 真实 Git Data API |
| 许可识别 | **真实**：条款特征匹配、`DETECTED/UNKNOWN/MIXED` 判定、未知即不展示 | 许可文件字节由替身提供 | 真实仓库许可文件 |
| 本地 dirty 判定 | **真实**：与 `git show HEAD:<path>` 字节比对 | — | — |
| 本地逃逸防护 | **真实**：`O_NOFOLLOW` + 逐段 symlink 检查 + dev/ino 复核 | — | — |
| 超时 / 重试 / 限流 / 重定向 / 流上限 | 真实的分支判定与状态映射逻辑 | `httpx.MockTransport` 合成 401/403/404/429/302/超大响应 | 真实端点产生的真实错误响应 |
| 持久缓存 | **真实**：真实写盘、真实校验和、真实过期、真实原子替换、真实 LRU 淘汰 | 缓存内容来自合成响应 | 跨真实仓库的缓存复用 |
| **代码执行** | **从不执行**第三方代码/Notebook/install 脚本（全模块无执行原语） | — | — |

---

## 2. 固定核验样例（离线，保留许可）

公开来源样例沿用仓库既有约定，**以固定字节存于** `tests/github_intelligence/conftest.py`，
测试运行**不访问外网**：

| 项 | 值 |
|---|---|
| commit（不可变） | `50113da16fec53b66b80d75e80a89296de4fa5a5` |
| 仓库 | `fastapi/fastapi` |
| 文件 | `docs_src/dependencies/tutorial001.py` |
| 符号 | `read_items`（function） |
| 行区间 | `L11`–`L14`（inclusive） |
| 许可 | MIT（`FROZEN_LICENSE_TEXT`，保留许可通知） |

> 只引用必要片段，并保留许可声明。该样例不可变 commit 优先。

---

## 3. 合成本地 Git 库（真实静态读取）

`test_source_failure_matrix.py` 与 `test_product_completion.py` 在 `tmp_path` 下用
**真实 `git` 可执行文件**建库并提交，然后由模块静态读取：

```bash
git init <root>
git -C <root> add .
git -C <root> -c user.name=... -c user.email=... commit -m synthetic
```

**真实发生的**：`git ls-files -z`、`git rev-parse HEAD`、`git show HEAD:<path>`、
真实文件字节读取与 SHA256。**不是** mock。
**未发生的**：不执行库内任何源码，不运行 install 脚本，不 import 目标模块。

---

## 4. 明确不予混同的几条

- **公开 API 读取 ≠ 模型讲解实测**。本模块不产出讲解；讲解由 tutor 侧（@fqf060420）负责。
- **AST 找到函数 ≠ 证明业务含义**。证据里 `relevance.status` 恒为 `CANDIDATE`/`UNCERTAIN`，
  理由字符串明写"不证明教学结论"。
- **合成响应通过 ≠ 真实端点通过**。见 §1 "未实测"栏。
- **无 token 只阻塞认证相关接口的实测**；公开读取与本地流程的实现与离线验证不受影响。
- **Mock 成功 ≠ 真实成功**；本模块不存在"真实失败却静默回退到 Fixture"的路径——
  真实模式出错一律抛出带 code 的 `SourceError`。

---

## 5. 外部阻塞清单

| 阻塞项 | 状态 | 需谁解除 |
|---|---|---|
| `C2C_GITHUB_TOKEN` 未配置 | 未实测认证路径（配额提升、私有范围行为） | Lead / 运维 |
| 本机未授权外网实测 | 未实测真实端点连通性与真实限流响应 | Lead 授权后由 Lead 复验 |
| 本机 venv 未按 `requirements/full-delivery-py312.lock` 安装 | 4 个文档模块测试 + 1 个 Lead 集成回归在本机失败。锁文件**已包含** `python-docx`/`python-pptx`/`pypdf`/`pillow`，CI 会装齐 → **这些失败在 CI 中预计不存在**，属本地环境未对齐 | 本机执行 `python -m pip install -c requirements/full-delivery-py312.lock -e ".[dev]"` 即可对齐（**不属本模块职责**，由 @inogi-sama 复验） |
