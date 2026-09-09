# Concept-to-Code Learning

> 当前候选：**完整模块交付 / PARTIAL**。Lead 已提供新接口、中央编排和来源笔记；三名成员完整模块尚未交付，真实文档/来源/模型链不能宣称可用。现有网页仍是明确标注的 Fixture 演示。查看 [完整范围与任务书](docs/full-delivery/PLAN.md)、[启动说明](docs/full-delivery/RUNNING.md)、[实际能力 API](docs/full-delivery/INTERFACES.md) 和 [审核材料](docs/delivery/lead/FINAL_REVIEW.md)。以下原演示说明保留。

文档学习 + AI 讲解 + GitHub 真实代码引用。用户围绕当前页、章节或选中文字提问，按自己的理解程度阅读讲解，核对真实源码，再主动保存有来源的个人笔记。

**0.2.0.dev0 · Phase 0.5 · FIXTURE / SCAFFOLD_DEMO**

当前可运行：三栏 React 界面、合成依赖注入讲义、四档固定讲解、FastAPI 官方代码的一条已核验冻结引用，以及真正持久化的本地笔记。它没有实时搜索、真实模型或完整 Office 解析。

## 运行

需要 Python 3.12；前端使用 Node.js 20.19+（CI 固定 Node 20）。从此仓库根目录运行：

```sh
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
ruff check .
pytest -q
python scripts/tutor.py doctor
python scripts/tutor.py demo
npm --prefix apps/web ci
npm --prefix apps/web test
npm --prefix apps/web run build
python scripts/tutor.py serve
```

在浏览器打开 http://127.0.0.1:8766 。保持该进程运行即可使用。开发时另开终端运行 `npm --prefix apps/web run dev`，前端将 `/api` 和 `/health` 转发到本地后端。

## 体验一次完整流程

1. 左栏阅读合成讲义，翻页或选中当前页的一句话。
2. 中栏保留示例问题“依赖注入到底是什么？真实项目中怎么使用？”，选择 Beginner / University / Engineering / Source-code level，点击“结合代码讲解”。
3. 右栏核对 `fastapi/fastapi`、Commit、文件、`read_items`、12–14 行及 MIT 许可证。此冻结片段没有运行，状态为 `NOT_RUN`。
4. 填写“我的补充”，点击“保存为学习笔记”。打开“我的笔记”，刷新或重启服务后仍能看到自己的文字和两类来源。

笔记默认位于忽略目录 `data/local/fixture-notes.sqlite3`；`C2C_DATA_DIR` 可指定独立目录。只提供新增与读取，没有自动覆盖。CLI demo 使用临时数据库，不修改 UI 笔记。演示报告位于忽略目录 `reports/learning-demo/`。旧 Phase 0 回归报告单独位于 `reports/demo/`。

## 目标边界

支持目标：PDF、PPTX、DOCX、Markdown；当前页/选区上下文；用户指定 GitHub 仓库、授权本地仓库、明确授权的公开 GitHub 搜索；四档讲解；来源笔记。Notebook、网页为后续扩展。

尚未实现：真实文件导入、实时 GitHub 搜索、任意仓库/Commit/文件/符号核验、本地模型推理、DGX 部署、多仓库比较及新片段的隔离运行。预留接口返回 `NOT_IMPLEMENTED`，不会生成虚假搜索结果。旧员工考核、隐藏评分与强制练习已退出比赛 MVP。

## 团队与协作

| 账号 | 主责 |
| --- | --- |
| @suiyisuixing | 产品、Skill、公共契约、后端集成、最终合并 |
| @inogi-sama | 文档阅读、页码/选区、三栏前端、笔记 UI |
| @zchzbjklg | GitHub 来源模式、固定 Commit、核验、证据卡、比较 |
| @fqf060420 | 知识点、讲解级别、本地模型、DGX、Grounding 评测 |

2026-09-09 API 已核验三名成员均为 Write，@suiyisuixing 为唯一 Admin、唯一最终审核人和 main 合并人。所有 PR 保留强制 phase0-checks；外部批准数为 0。成员 PR 由 Lead 审核；Lead 自有 PR 经人工自检、Codex 审计、CI 且无 P0/P1 后可自行合并。团队建议非阻塞。详见 [Lead 合并政策](docs/governance/lead-controlled-merge-policy.md)、[协作指南](CONTRIBUTING.md)、[分工](docs/roles-and-ownership.md)。

## 导航

[SKILL](SKILL.md) · [产品范围](docs/product-scope.md) · [重构决策与历史](docs/rescope-decision.md) · [架构](docs/architecture.md) · [六个契约](docs/data-contracts.md) · [API](docs/api.md) · [来源核验](demo/learning/README.md) · [安全](SECURITY.md)

现有仓库直接改名，ID `1360182264` 不变。基线 Commit `8c487316ccf598b0a549803d3cff3814302633c3` 和 `pre-rules-v0.1.0` 标签保留。PR #56 已合并，`pre-rules-v0.2.0` 固定在 `e83a64d63a78f11534fbe51631775ceeb3885ccb`；历史标签保持原指向。本次不创建 GitHub Release 或新 Tag。

## Sprint 1 合同准备

版本化合同与 `/api/sprint-1` 由 [PR #58](https://github.com/suiyisuixing/concept-to-code-learning/pull/58) 引入；请核验该 PR 是否已进入 main。治理文档本身不引入运行时代码。详见 [Sprint 1 接缝](docs/sprint-1-first-real-vertical-slice.md) 与 [角色提示词](docs/codex-prompts/lead-integration.md)。这些合同及 Fixture 不代表真实 PPTX、通用 GitHub 核验或模型已完成。
