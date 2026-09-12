# 代码库学习工作区：交付与审计

2026-09-12 · Lead · 关联 #65（扩展工作区与中央学习流程）

本候选增加「代码库 → 知识」入口，保留「文档 → 知识与代码」入口。
从已合并 main `f02f65f4e9c6627d4ebd9b6099e8d6d265b74600` 开发，分支
`feat/repository-learning-workspace`。本报告不是人工批准或 main 合并证明。

## 现在能做什么

- 文档仍支持 PDF、PPTX、DOCX、Markdown；顶部切换学习材料类型。
- 添加公开 GitHub 仓库地址，或按仓库名称搜索；多个仓库各自显示目录树。
- 文件夹保留原层级；打开文件时读取源码。目录过大时逐级加载，支持分页和文件名查找。
- 源码保留行号，可鼠标划选、点击行号、Shift 扩选、键盘移动，再提问或写批注。
- AI 收到当前固定版本文件、选区及实际读取的少量关联文件，不要求另填通用知识点。
- 延用可选模型、分段显示回答、取消、错误重试；回答中的代码依据可定位回文件与行号。
- 代码批注、会话和来源笔记可保存、重启恢复、导出；切回文档时保留各自阅读位置。

## 边界与兼容

仓库目录与每次打开的文件固定到 Git Commit。文件原始字节验证长度与 Git blob SHA，
另保存 SHA-256；关联文件和许可同样绑定这一版本。缓存损坏会停止读取。
不克隆或执行第三方项目，不运行 Notebook，不读取用户的 GitHub 登录凭据。

新增 `CODE`、`CodeLocation` 和仓库接口属于 `full-delivery-v1` 的增量扩展，
由本次 Lead 功能请求授权。未修改 `schemas/sprint-1` 或旧 API。
旧记录中没有的新字段不序列化为 null/空数组，保持既有笔记与来源指纹。
新仓库数据库独立于已有文档/笔记数据库；测试数据未写入用户资料目录。

GitHub 目录递归响应可能截断；实现按官方约定退回逐级树读取，不会把不完整结果
当作完整仓库。源码链接与子模块在目录中保留，但不跟随执行或任意取回。
依据：[Git trees](https://docs.github.com/en/rest/git/trees?apiVersion=2022-11-28)、
[Repository contents](https://docs.github.com/en/rest/repos/contents?apiVersion=2022-11-28)。

## 实际验证

| 层面 | 证据与结论 |
| --- | --- |
| implementation | 仓库树、源码阅读、CODE 上下文、批注/笔记、引用跳转已实现 |
| module_tests | macOS Python 3.12：486 passed；前端：37 passed；Ruff 与生产构建通过 |
| contract | full-delivery-v1 Schema/OpenAPI 检查 CURRENT；旧格式兼容包含在全量测试中 |
| failure tests | 截断目录、中文/emoji 选区、路径穿越、链接/子模块、大文件、字节不匹配、未知许可、搜索限流、引用 ID 伪造、迟到响应、保存恢复均有受控测试 |
| live_external_check | 实际读取公开 karpathy/micrograd，固定 `7bc720e951fe422b8f8814aa5aa1b64121d26b4c`，读取 nn.py 与 engine.py；无仓库代码执行 |
| integrated_product | 两个现有本地模型完成三次请求、源码引用绑定和笔记快照保存；原生鼠标选区、批注保存/刷新和引用跳转已操作核对 |
| target_hardware | macOS 本机浏览器与已安装 MLX 模型；窄屏是 CSS 响应式窗口验证，不是手机硬件验收；Linux/Windows 以本 PR 最新 CI 为准，未重新宣称 DGX 验收 |
| lead_review | Codex 自审与独立设计复审；人工关键文件检查及最终合并决定未代填 |

`doctor` 和 `demo` 均成功；demo 是 Fixture，只验证原有演示入口。
所有自动化外部替身均标注在测试文件中，不计入真实 GitHub/模型通过数量。

最新同机两次请求：Coder 7B 首段 6.45 秒、完成 19.61 秒；Qwen3 4B 首段
2.28 秒、完成 14.29 秒。它们不是通用性能保证。代码模式省去模型搜索规划调用，
重复打开已缓存文件无需重新下载；大仓库首次目录读取仍受网络与 GitHub 限流影响。

另实测 `trekhleb/javascript-algorithms` 固定版本
`85293e3e2b88f4d2ce330d956b139cf628aa1e82` 的 Dijkstra 实现：模型正确区分
返回距离/前驱对象与完整路径数组。首段 6.19 秒、完成 11.12 秒，来源笔记保存成功。
具体场景见 [验证记录](repository-workspace-validation.json)。

## 内容质量审计：部分通过

源码身份、字节、行号、选区、引用范围与许可属于确定性校验；这些检查不能证明
模型的解释正确。实际小模型回答仍出现过：把没有参与当前加权求和的 `__pow__`
一起归因到计算过程；把链式法则中的最终目标导数误写成 `dz/dz`。
因此本候选的语义正确性记录为 **PARTIALLY VERIFIED**，没有声明全量内容验收通过。

已改进完整文件上下文保留、Python 嵌套符号范围和简单比较边界事实，减少混淆。
这些分析只解析文本，不运行代码，也不证明业务含义。一次额外模型复核实验产生
误拒绝且增加延迟，已移除；当前发布代码不以另一轮模型自检冒充正确性认证。
模型可由用户在既有设置中选择；没有新增下载、付费服务或自动云端回退。

## 设计复核

Impeccable 独立复审要求移除空状态装饰性短标语、将活动文件侧线减为 1px；
两项均在一次修正后评为 resolved，最终 disposition 为 ship。此结论只覆盖所列
设计修正，不能代替模型语义或实体移动设备验收。桌面与窄屏截图均已检查。

## 已知限制

- 此入口读取**公开**仓库；没有新增私有 GitHub 账号连接。原有授权本地来源流程保留。
- 完整目录按需加载，不把整个仓库一次塞入模型。最多读取两个静态可解析的关联文件，
  每个最多约 4,000 字符；当前文件按阅读段与选区限长。动态导入、跨语言调用等不保证解析。
- 二进制、非 UTF-8、单文件超过 1 MiB、过长压缩行、许可未确认的文件给出原始 GitHub 链接。
- 截断的大目录只能搜索已经读取的目录，界面明确显示这一范围。
- 本地保存的是固定版本；重新添加仓库可加载更新版本，旧批注和笔记保留原版本。
- 新工作区没有编辑或提交 GitHub 源码的功能；可以编辑问题、批注和个人笔记。

## 可重复检查与安装回滚

在独立环境设置 `PYTHONPATH=src`（或将本工作区安装为 editable），运行：

```sh
python -m ruff check .
python -m pytest -q
python scripts/export_full_contracts.py --check
python scripts/tutor.py doctor
python scripts/tutor.py demo
npm --prefix apps/web test
npm --prefix apps/web run build
```

本地运行用已有 `scripts/desktop.py --port 18766 --no-browser` 启动入口。
安装从确切候选提交构建，先备份既有数据与启动配置，校验原有文件哈希，保留旧
release。候选安装不会自动合并 main。运行证据、原始截图和数据备份保留在本地
`repository-workspace-20260912-032105Z` 交付目录，不提交私有资料或第三方代码副本。
