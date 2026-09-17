# 依赖说明 — github_intelligence（@zchzbjklg）

**Issue**: #67 · **模块**: `src/concept_to_code_learning/github_intelligence/`
**声明文件**: `deps/zchzbjklg.txt`

## 概要

本模块**不新增任何运行时或测试依赖**。运行时依赖仅为项目已有的
`httpx`（products）与 `jsonschema`（products）；测试依赖仅为 `pytest`、`httpx`（dev）。

## 运行时依赖

| 依赖 | 用途 | 来源 |
|---|---|---|
| `httpx` | 异步 GitHub 公开读取（`api.github.com`） | 已在 `[project.optional-dependencies].dev`（`httpx==0.28.1`） |
| `jsonschema` | 契约校验（项目既有） | 项目既有 product 依赖 |
| Python 标准库 | `asyncio` / `ast` / `hashlib` / `base64` / `re` / `pathlib` / `os` / `stat` / `subprocess`(local) / `time` / `tempfile` | 标准库 |

## 测试依赖

| 依赖 | 用途 | 是否新增 |
|---|---|---|
| `pytest` | 测试运行器 | 否（既有 dev） |
| `httpx` | `httpx.MockTransport` 合成响应 | 否（既有 dev） |
| Python 标准库 | `asyncio` / `base64` / `hashlib` / `re` / `subprocess`(合成 Git 库) / `time` | 标准库 |

**未引入 `pytest-asyncio`**：异步用例一律用 `asyncio.run()` 在独立事件循环中包裹，
保持 `pyproject.toml` 不动。

## 凭据与环境变量

| 变量 | 用途 | 是否新增 |
|---|---|---|
| `C2C_GITHUB_TOKEN` | GitHub 只读 token（可选，提升配额） | 否（由 `ProviderSettings.from_env` 读取，Lead 既有） |
| `C2C_LOCAL_ROOTS_JSON` | 本地授权根目录 JSON 数组 | 否（既有） |

- Token 只由后端从 `ProviderSettings.github_token` 读入，**只**附加到 `api.github.com` 请求；
  **不进** 异常、日志、磁盘缓存或浏览器。有测试断言持久化缓存文件不含 token 明文。
- 本模块不自行启动付费模型 API、不批量下载、不调用任何需要额外授权的服务。

## 与 CI 锁文件的关系

`requirements/full-delivery-py312.lock`（CI 使用的锁）已包含 `httpx==0.28.1`、`pytest==9.1.1`，
以及文档模块的 `python-docx`/`python-pptx`/`pypdf`/`pillow` 等。本模块**不依赖**这些文档依赖；
它们属于 @inogi-sama 的模块。本机若未按锁文件安装，只会影响文档模块测试，**不影响本模块**。

## 对齐命令（供复验）

```bash
python -m pip install -c requirements/full-delivery-py312.lock -e ".[dev]"
```

与 `.github/workflows/ci.yml` 的安装步骤一致。
