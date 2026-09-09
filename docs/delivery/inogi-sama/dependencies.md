# inogi-sama 依赖申请

由 Lead 汇总到正式后端依赖与锁文件；本角色未修改根 `pyproject.toml`。

| 包 | 固定版本 | 用途 | 许可 |
|---|---:|---|---|
| PyMuPDF | 1.26.4 | PDF 物理页、文字块与原版 PDF 预览 | AGPL-3.0-or-later / commercial，Lead 合并前需确认分发策略 |
| python-pptx | 1.0.2 | PPTX Slide、文本框、表格和图片 | MIT |
| python-docx | 1.2.0 | DOCX 标题、段落、表格和图片 | MIT |

2026-09-09 本机两次 PyPI 安装均因代理重置/TLS EOF 失败，未把安装失败写成解析器测试通过。
