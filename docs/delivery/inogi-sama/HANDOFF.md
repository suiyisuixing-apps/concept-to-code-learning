# inogi-sama 完整模块交付记录

状态：`MODULE_READY_FOR_LEAD_REVIEW`
Lead 审核：`PENDING`  
基线：`origin/feat/full-learning-integration@90fb42f3bdb7b88a1a6d3ddea27de88a260b9ea1`
基线性质：`UNMERGED_CONTRACT`，不是 main。

## 实现

- `documents/full.py` 实现完整 `DocumentProvider` 工厂与七个异步方法。
- 文件名/魔数/Office 内部结构校验；拒绝损坏包、路径穿越、外部关系、超量解包和超量资产。
- 内容 SHA256 文档 ID、UTC 时间、UTF-8 JSON、每文档只读原件副本、原子 staging；失败仅清理本次 staging。
- PDF 按物理页提取 bbox 文字并以原 PDF 作为服务端资产；空白/扫描页标 `NO_EXTRACTABLE_TEXT`，不伪造 OCR。
- PPTX 保留 Slide、文本框、表格、图片和标题层次；图表标 unsupported；明确学习视图差异。
- DOCX 按标题路径切 section，保留段落/表格稳定 block ID 和图片资产，不编造物理页码。
- Markdown 仅输出纯文本/代码块，剥离 HTML，去除 javascript/data/file 危险链接目标。
- React 工作台接入 full-delivery-v1：导入、导航、DOM 选区到 Unicode code point、session revision、迟到响应丢弃、四级讲解、三种来源授权、候选选择、比较、取消、来源卡和笔记 CRUD/搜索/导出。
- 当前单元搜索与整块选择；原始、改编和 AI 生成代码按 provenance 分开展示，运行状态独立显示。
- 模型未配置与许可未知、无代码、空数据等状态明确可见；来源链接只用服务端 permalink。

## 验证证据

| 类别 | 命令 | 结果 |
|---|---|---|
| frontend install | `npm --prefix apps/web install --save-dev vitest@4.1.11 @vitest/mocker@4.1.11` | exit 0；安全修复版写入 package/lock |
| component tests | `npm --prefix apps/web test -- --reporter=verbose` | exit 0；1 file / 9 tests passed |
| production build | `npm --prefix apps/web run build` | exit 0；31 modules；JS 212.10 kB |
| dependency audit | `npm --prefix apps/web audit` / `audit --omit=dev` | 均 exit 0；0 vulnerabilities |
| ruff | `.venv/Scripts/ruff check .` | exit 0 |
| document module/API | `.venv/Scripts/python -m pytest -q tests/documents` | exit 0；9 passed；真实 PDF/PPTX/DOCX/Markdown |
| existing stories | `pytest tests/full_delivery/test_stories.py` | exit 0；9 passed |
| existing contracts | `pytest tests/full_delivery/test_contracts_and_skill.py -k "not portable..."` | exit 0；11 passed / 1 deselected |
| existing boundaries | `pytest tests/full_delivery/test_boundaries.py -k "not uninstalled..."` | exit 0；34 passed / 1 deselected |
| doctor/demo/schema | `python scripts/tutor.py doctor`; `demo`; `export_full_contracts.py --check` | 均 exit 0；Schema CURRENT |
| browser desktop/narrow | 本地 `start` + in-app browser；默认桌面及 390x844 | 真实 Markdown 上传 201、units/context 200；无重叠；AX 状态见 `BROWSER_VALIDATION.md` |
| live external source/model | 未执行 | 属其他角色；没有 Token/模型端点，不计验收 |
| integrated product | 未执行 | Tutor/Source 真实模块与本机 Python 环境未就绪 |
| target hardware | 未执行 | `NOT_TESTED` |

## Mock 与真实边界

前端组件测试使用明确 fetch Mock，只验证组件状态与请求交互，不代表真实 Tutor、来源核验或 Notes 持久化。Provider/API 测试使用真实本地文件；PDF/PPTX/DOCX 测试均在 Python 3.12 中生成并解析真实二进制。浏览器实测使用真实 Markdown Provider 和真实 Session/Context API；Source/Tutor 未交付时按真实 capability 显示 unavailable，没有 Fixture 回退。

## 已知限制和风险

- 扫描 PDF 不做 OCR；原 PDF 可读，文字状态为 `NO_EXTRACTABLE_TEXT`。
- Office 是结构化学习视图，不保证动画、公式、图表或像素级排版；原件保留但当前公共资产 API 只允许 PDF/图片，不能直接返回 Office 包。
- PyMuPDF 的 AGPL/commercial 许可需要 Lead 在汇总依赖前决定是否接受；可改用 pypdf + 独立预览策略。
- Lead 共享测试 `test_uninstalled_modules_report_partial_without_fixture_fallback` 仍要求 Document Provider unavailable；本 PR 交付 Provider 后该旧断言需要 Lead 在集成分支更新。本角色未越权修改 `tests/full_delivery/`。
- `test_portable_skill_package_runs_complete_controlled_http_workflow` 在原生 Windows 将子进程环境缩减为 PATH/HOME/PYTHONIOENCODING 后，标准库 loopback 客户端返回 `INVALID_INPUT`；同文件其余 11 项通过。Lead 的既有 Linux 证据为通过，本角色未修改 Skill 客户端。

## Lead 五分钟复验

1. 使用 Python 3.12 安装项目 dev 依赖和 `deps/inogi-sama.txt`。
2. 运行 `ruff check .` 与 `pytest -q --basetemp=.test-work`。
3. 运行 `npm --prefix apps/web ci && npm --prefix apps/web test && npm --prefix apps/web run build`。
4. 启动本地 API 与 Vite，依次导入测试生成的 PDF/PPTX/DOCX/Markdown；核对空白 PDF、Office 学习视图警告、emoji 选区和窄屏布局。
5. 在 Source/Tutor 使用明确 Fixture 时只验 UI；接入真实 Provider 后另行记录 integrated/live_external，不把 Fixture 当真实验收。

`MODULE_READY_FOR_LEAD_REVIEW`：本角色范围、真实四格式测试、前端安全升级和浏览器流程已完成。`lead_review` 仍为 `PENDING`；Source/Tutor 真实外部实测和上述两个 Lead 共享测试由 Lead 集成处理，未计为本角色真实验收。
