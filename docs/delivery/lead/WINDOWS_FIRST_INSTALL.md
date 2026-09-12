# Windows 首次安装与修补验收

2026-09-12 · Lead · 关联 #65、依赖 PR #75。此记录是本机开发验收，不是人工批准或合并决定。

## 安装基线与运行

从私有仓库功能分支 `feat/repository-learning-workspace` 首次克隆，核实远端 Head
为 `48f9c76564e2f91e8b6276e5619734ec8b8ac67d`；PR #75 当时仍开放、未合并。
本次修补分支为 `codex/windows-first-install`，PR 目标是该功能分支，仅包含新增差异。

本机 Windows 11 Pro 10.0.26200 x64，Intel Core Ultra 7 270K Plus（24 核），
95.28 GiB RAM，RTX 5060 8151 MiB，驱动 591.86。复用 Python 3.12.14，
项目独立 `.venv`；另置官方 Node 22.23.2 便携版。保留现有 Node 24、Python 与 Conda，
没有修改全局解释器、驱动或 CUDA 安装。依赖使用项目锁定版本；前端安装禁用依赖脚本。

仓库的 `Start-ConceptToCode.cmd` 调用项目 Python，默认网页端口 18766；
它要求 endpoint 模型服务已运行。本机另有桌面快捷方式，负责启动已安装模型与工作台。
本地 `desktop.json` 明确填写 `/v1/models` 返回的模型 ID 和绝对 `data_dir`，UTF-8 无 BOM。
Codex MSIX 对 LocalAppData 的重定向已实测，本机快捷方式使用解析后的真实目录，
避免从普通桌面启动时连接到不同数据目录。安装信息和机器路径保留在本机，未提交模型或配置。

## 本轮修补

- 关联源码被读取预算截短时，沿用已有 warnings 字段说明，并正确设置 `input_truncated`。
- 历史对话的单轮问题、答案或概念被裁剪时，正确设置截断指标。
- 不扩大模型输入预算，不修改共享 Schema，不迁移或回写旧笔记；旧快照不能补造当时未记录的信息。
- 测试副本排除 `artifacts`，避免临时根在本项目内时递归复制验收产物。
- 增加 Windows 启动入口与首次环境/独立数据目录说明。
- CI 仅为 `pull_request` 增加精确目标 `feat/repository-learning-workspace`，使叠加修补 PR
  也运行现有 Linux/Windows 两项检查；仍仅 push main、只读权限、每项 10 分钟，无矩阵或定时运行。

## 软件与接口验收

| 项目 | 实际结果 |
| --- | --- |
| Ruff | PASS |
| Python 全量 | 490 passed、1 skipped；跳过原因是本机不允许创建测试符号链接 |
| 前端 | 37 passed；Node 22 生产构建成功 |
| 合同导出检查 / doctor | CURRENT / PASS |
| demo | PASS，明确仅 Fixture |
| 合成 Markdown、DOCX、PPTX、PDF | 真实页面导入与阅读通过；PDF 原版画布正常 |
| 两个公开仓库 | 固定版本匿名读取、目录展开、源码行号通过；未使用管理员凭据 |
| 选区与批注 | 网页鼠标拖选、行号/Shift 选区、中文 emoji 批注、刷新恢复通过 |
| 真实模型 | 模型列表、实际 ID 选择、流式预览/最终解析通过 |
| 停止与重试 | 收到真实预览后停止，llama.cpp 确认 cancel 且恢复 idle；问题保留、未保存临时回答。受控连接失败后实际模型重试成功 |
| 来源笔记与引用 | 笔记保存、固定版本引用跳转、三案例笔记/批注/会话随应用重启恢复通过 |
| 多模型切换 | NOT RUN：本机只有一个获准下载的真实模型，未伪造第二个模型 ID |
| 人工审核 | PENDING；Codex 独立差异审核未发现 P0/P1 实现阻塞，未代填人工决定 |

首次默认 pytest 临时目录无访问权限，改用仓库外新的独立临时根后完成全量；
没有更改用户目录权限或用全局编码开关掩盖问题。另一次测试中途修改 CI 范围导致旧加载断言失败，
在代码稳定后重新执行全量得到上述最终结果。两个依赖弃用警告保留，未因此升级锁定依赖。

## 真实模型与速度

用户单独授权下载官方 [Qwen2.5-Coder-7B-Instruct-GGUF](https://huggingface.co/Qwen/Qwen2.5-Coder-7B-Instruct-GGUF)，
Q4_K_M，4,683,073,536 bytes，Apache-2.0；revision
`13fb94bfda8c8cf22497dc57b78f391a9acb426a`，官方 SHA256
`509287f78cb4d4cf6b3843734733b914b2c158e43e22a7f4bf5e963800894d3c`，下载后匹配。

实际服务 `http://127.0.0.1:18767/v1`，实际 ID `Qwen2.5-Coder-7B-Instruct-Q4_K_M`。
后端为官方 [llama.cpp b10809](https://github.com/ggml-org/llama.cpp/releases/tag/b10809)，
commit `5266f24da`，Windows CUDA 13.3 便携构建；29/29 层 GPU，8192 上下文，
单并发，K/V 缓存 q8_0，Flash Attention，禁止 context shift。离线读取已安装权重，
不执行第三方代码，无付费 API、云回退或开发 GitHub 凭据注入。

同一简短模型直连问题：Vulkan/F16 KV 首字 6.461 秒、总 31.744 秒；
Vulkan/Q8 KV 为 1.245/2.171 秒；最终 CUDA/Q8 为 0.253/1.159 秒、约 80.57 token/s。
最终显存约 6018/8151 MiB。首次编译、缓存与后端同时存在差异，不能把全部加速归于单个参数。
这些直连数字不代替完整工作台性能；浏览器 engine 案例另测首段实际显示约 0.522 秒、完成 2.720 秒。

## 三个固定源码案例与内容质量

沿用 `repository-workspace-validation.json` 的原问题与固定 commit：
micrograd `7bc720e951fe422b8f8814aa5aa1b64121d26b4c`，javascript-algorithms
`85293e3e2b88f4d2ce330d956b139cf628aa1e82`。本次完整当前单元、Source-code 等级、初始无历史。
旧 Mac 记录未包含原选区、全部参数与完整输入，不能声称逐字复现旧请求。

| 案例 | HTTP 首段 / 完成 | 内容判断 |
| --- | --- | --- |
| micrograd/nn.py | 1.367 / 4.983 秒 | 加权和主体正确、未误归因 pow；省略 nonlin 分支及部分反向传播细节，PARTIAL |
| micrograd/engine.py | 0.697 / 2.897 秒 | 累加动机大致正确，但更新方向含混、遗漏实际链式乘法和 reversed(topo)，FAIL |
| dijkstra.js | 0.871 / 2.158 秒 | 正确区分 distances/previousVertices 与尚未重建的完整路径数组，PASS（限定此问题） |

每例记录实际 HTTP messages、参数、原始 SSE、模型 ID、首段与总时长、最终回答。
三例每例一次实际生成，`temperature=0`、`max_tokens=1600`、finish_reason=stop，
输入无裁剪、没有输出修复，原始模型 answer 与最终 API 文本一致。
nn 的输入包括 engine.py 全部 94 行；界面 engine 引用卡 L1–67 是 2000 字符引用摘录范围，
不是模型输入只读 67 行。关联源码、选区和解析检查不能认证语义正确。

浏览器独立重测 engine 问题还生成了源码不存在的 `out.grad += other.data * out.grad`，
该错误已保存截图与原回答，未标为成功的内容验收。三例没有证据指向源码读取丢失、编码或前端吞字；
错误存在于生成内容中，不能据此断定模型大小是唯一原因。
当前 GGUF Q4_K_M/CUDA 与旧 Mac MLX 4bit 的量化、后端和调用条件不同，不能简单归因于 Windows/Mac。

## 证据位置与边界

本机原始资料在 `artifacts/windows-install/`（Git 忽略）：安装/测试日志、合成文档、
页面截图、`context-audit/` 的完整发送包与截断前后复现、`live-model/run-20260912T062339Z-2e4492/`
的三例 HTTP/SSE/原始回答、保存与恢复记录；`browser-history.json`、
`browser-timing-and-cancel.json`、`browser-cancellation.json` 保存浏览器证据。
模型发布校验、GPU 日志和启动入口检查保存在实际应用目录的 `logs/`。
这些资料仅留在本机，不将第三方源码副本、模型、会话 ID 或机器私有路径提交仓库。

结论：Windows 安装与主要功能可运行；真实模型链路已验证，**讲解内容整体仅部分通过**。
单模型环境尚不能验收真实多模型切换。现有设计、旧接口、数据库与人工审核边界保留。
