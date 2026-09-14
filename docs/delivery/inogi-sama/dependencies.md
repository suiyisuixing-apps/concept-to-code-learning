> 历史记录（成员依赖提案）。保留原有结果与限制，不用于声明当前候选已验收；当前范围见 [../lead/DEPENDENCIES.md](../lead/DEPENDENCIES.md)。

# inogi-sama 依赖申请

由 Lead 汇总到正式后端依赖与锁文件；本角色未修改根 `pyproject.toml`。

| 包 | 固定版本 | 用途 | 许可 |
|---|---:|---|---|
| PyMuPDF | 1.26.4 | PDF 物理页、文字块与原版 PDF 预览 | AGPL-3.0-or-later / commercial，Lead 合并前需确认分发策略 |
| python-pptx | 1.0.2 | PPTX Slide、文本框、表格和图片 | MIT |
| python-docx | 1.2.0 | DOCX 标题、段落、表格和图片 | MIT |

2026-09-09 最终在仓库 `.venv`（Python 3.12.14）安装成功，真实四格式测试 9/9 通过。根 `pyproject.toml` 和后端锁文件保持不变，等待 Lead 汇总。
