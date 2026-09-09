# inogi-sama 完整模块交付记录

状态：`PARTIAL_WITH_EXTERNAL_DEPENDENCY_BLOCKER`  
Lead 审核：`PENDING`  
基线：`origin/feat/full-learning-integration@53dc7bb`（晚于首次发布 `4b1d37d`）  
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
- 模型未配置与许可未知、无代码、空数据等状态明确可见；来源链接只用服务端 permalink。

## 验证证据

| 类别 | 命令 | 结果 |
|---|---|---|
| frontend install | `npm --prefix apps/web ci` | exit 0；157 packages；npm 报 2 个 moderate 审计项，未执行破坏性强制升级 |
| component tests | `npm --prefix apps/web test -- --reporter=dot` | exit 0；1 file / 4 tests passed |
| production build | `npm --prefix apps/web run build` | exit 0；30 modules；JS 210.79 kB |
| ruff scoped | `ruff check src/concept_to_code_learning/documents tests/documents` | exit 0 |
| safe/Markdown tests | `PYTHONPATH=src python -m pytest ... -k "markdown or selection or wrong_magic or external" --basetemp=...` | exit 0；4 passed / 3 deselected |
| full pytest | `PYTHONPATH=src python -m pytest -q` | collection blocked：当前 Python 缺 FastAPI（不是断言失败） |
| parser dependencies | `python -m pip install -r deps/inogi-sama.txt` | blocked：代理 reset / TLS EOF |
| PDF/PPTX/DOCX real tests | `tests/documents/test_full_provider.py` | 已编写，现场未执行；缺三项解析依赖，不计真实验收 |
| live external source/model | 未执行 | 属其他角色；没有 Token/模型端点，不计验收 |
| integrated product | 未执行 | Tutor/Source 真实模块与本机 Python 环境未就绪 |
| target hardware | 未执行 | `NOT_TESTED` |

## Mock 与真实边界

前端组件测试使用明确 fetch Mock，只验证组件状态与请求交互，不代表真实 Tutor、来源核验或 Notes 持久化。Markdown Provider 与安全失败路径使用真实本地文件。PDF/PPTX/DOCX 测试生成真实二进制格式，但因安装端点失败尚未运行，不能列为通过。

## 已知限制和风险

- 扫描 PDF 不做 OCR；原 PDF 可读，文字状态为 `NO_EXTRACTABLE_TEXT`。
- Office 是结构化学习视图，不保证动画、公式、图表或像素级排版；原件保留但当前公共资产 API 只允许 PDF/图片，不能直接返回 Office 包。
- PyMuPDF 的 AGPL/commercial 许可需要 Lead 在汇总依赖前决定是否接受；可改用 pypdf + 独立预览策略。
- 前端锁文件已有 npm 报告的 2 个 moderate transitive audit 项，未绕过锁文件或强制升级。

## Lead 五分钟复验

1. 使用 Python 3.12 安装项目 dev 依赖和 `deps/inogi-sama.txt`。
2. 运行 `ruff check .` 与 `pytest -q --basetemp=.test-work`。
3. 运行 `npm --prefix apps/web ci && npm --prefix apps/web test && npm --prefix apps/web run build`。
4. 启动本地 API 与 Vite，依次导入测试生成的 PDF/PPTX/DOCX/Markdown；核对空白 PDF、Office 学习视图警告、emoji 选区和窄屏布局。
5. 在 Source/Tutor 使用明确 Fixture 时只验 UI；接入真实 Provider 后另行记录 integrated/live_external，不把 Fixture 当真实验收。

未写 `MODULE_READY_FOR_LEAD_REVIEW`：依赖安装阻塞使三种真实格式测试和浏览器端到端截图尚无现场证据。
