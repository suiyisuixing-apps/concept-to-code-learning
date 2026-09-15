# 依赖说明 — tutor / runtime / teaching / evaluation（@fqf060420）

**Issue**: #68 · **模块**: `src/concept_to_code_learning/tutor/`、`runtime/`、`teaching/`、本角色评测
**声明文件**: `deps/fqf060420.txt`

## 概要

本模块**不新增任何运行时或测试依赖**。运行时仅用项目既有 product 依赖
`httpx` 与 `pydantic`（以及标准库）；测试依赖仅为既有的 `pytest`、`httpx`（dev）。
与 Lead 的依赖分析及 `requirements/full-delivery-py312.lock` 一致。

## 运行时依赖

| 依赖 | 用途 | 来源 |
|---|---|---|
| `httpx` | 本地 OpenAI-compatible 端点的同步/流式调用（`runtime/local_model.py`、`runtime/async_model.py`） | 既有 product 依赖（`httpx==0.28.1`） |
| `pydantic` | 讲解计划/输出的 schema 校验（`tutor/full.py`） | 既有 product 依赖（`pydantic==2.13.5`） |
| Python 标准库 | `asyncio` / `json` / `hashlib` / `urllib` / `socket` / `ipaddress` / `dataclasses` / `pathlib` / `time` | 标准库 |

## 测试依赖

| 依赖 | 用途 | 是否新增 |
|---|---|---|
| `pytest` | 测试运行器 | 否（既有 dev） |
| `httpx` | `httpx.MockTransport` / 本地合成 HTTP 服务模拟模型端点 | 否（既有 dev） |
| Python 标准库 | `asyncio` 等 | 标准库 |

**未引入 `pytest-asyncio`**：异步用例在独立事件循环中运行，保持
`pyproject.toml` 不动。测试不访问外网、不要求真实模型端点；真实模型
运行作为 REAL_RUN 证据单独报告（见 issue #78/#79/#80 的 14B/27B 实测记录），
不混入 module_tests。

## 凭据与环境变量

| 变量 | 用途 | 是否新增 |
|---|---|---|
| `C2C_MODEL_BASE_URL` | 本地模型端点（默认 loopback） | 否（`ProviderSettings.from_env` 既有） |
| `C2C_MODEL_ID` | 服务端模型 ID，响应身份不一致即拒绝 | 否（既有） |
| `C2C_MODEL_API_KEY` | 端点鉴权（仅后端持有） | 否（既有） |
| `C2C_MODEL_NETWORK_AUTHORIZED` | 非 loopback 端点的显式授权开关，默认 `0` | 否（既有） |

- Key 只由后端从 `ProviderSettings.model_api_key` 读入并仅附加到已配置的模型端点；
  **不进** 异常、日志、磁盘或浏览器。
- 默认 loopback；远程/DGX 端点需显式授权并说明数据流向。**不自动回退云端、
  不下载模型权重、不产生任何费用**；新模型下载须用户显式授权。
- 模型断连如实返回 `MODEL_OFFLINE` / 相应错误码，无 fallback 假响应（#12 红线）。

## 硬件边界

`deploy/dgx/` 为纯文档（运行时支持说明、配置模板、容量估算依据）。
未接 DGX 实机，状态 **NOT_RUN**（#13 / #68 C8），不从本机小模型结果推断成功。

## 与 CI 锁文件的关系

`requirements/full-delivery-py312.lock`（CI 使用的锁）已包含 `httpx==0.28.1`、
`pydantic==2.13.5`、`pytest==9.1.1`。本模块**不依赖**文档解析类依赖
（`python-docx`/`python-pptx`/`pypdf` 属 @inogi-sama 模块）；本机若未按锁文件
安装，只影响文档模块测试，**不影响本模块**。

## 对齐命令（供复验）

```bash
python -m pip install -c requirements/full-delivery-py312.lock -e ".[dev]"
```

与 `.github/workflows/ci.yml` 的安装步骤一致。
