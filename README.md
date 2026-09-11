# Concept-to-Code Learning

导入学习材料，在旁边提问，用可核对的真实代码理解概念，再保存自己的来源笔记。

当前为 **0.2.0 完整产品候选，等待 Lead 人工验收**。四格式阅读器、三种来源模式、两阶段真实模型教学和笔记已整合；2026-09-11 在 Apple Silicon Mac 上完成真实本地模型与公开 GitHub 案例。实际验收范围见 [最终审核](docs/delivery/lead/FINAL_REVIEW.md)。本分支尚未进入 main。

## 开始使用

已有 Python 3.12、Node 22.13+。在仓库中创建独立虚拟环境，一次安装并构建：

```sh
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -c requirements/full-delivery-py312.lock -e ".[dev]"
npm --prefix apps/web ci --ignore-scripts
npm --prefix apps/web run build
python scripts/desktop.py
```

最后一条是日常启动入口，会打开本地浏览器。未配置模型时可以阅读和管理笔记；配置好后使用真实 AI。[macOS/Windows 配置、模型接入、数据备份与停止方法](docs/full-delivery/RUNNING.md)。启动器不下载模型。

## 学习流程

1. 导入 PDF、PPTX、DOCX 或 Markdown，切换页面/章节。按住鼠标左键划选原文，或用「选整段」快速引用。
2. 选中的原句自动进入对话框，可直接改写问题；已有的自定义问题会保留。点击「写批注」可保存自己的理解，不需要启动模型。详见[划选与批注](docs/delivery/lead/SELECTION_ANNOTATIONS.md)。
3. 选择 Beginner、University、Engineering 或 Source-code。
4. 公开仓库留空时只学习文档。填写 `owner/repo` 并允许联网，可自动寻找代码；公开搜索需单独确认通用搜索词。本地模式只展示预先授权的仓库。
5. 点击「开始讲解」，核对来源卡上的固定 Commit、文件、行号、许可与原始代码。继续追问沿用冻结来源；高级选项可以比较两个仓库。
6. 填写「我的理解」并保存。笔记支持搜索、修订、Markdown/JSON 导出及重启恢复。

PDF 保留原始页面；Office 提供结构化学习视图，保留可提取的段落、表格与内嵌图片，并显示无法呈现的对象。DOCX 以章节定位；扫描 PDF 需要额外 OCR，本版没有自动 OCR。

## 来源与数据

代码核验包括仓库公开属性、固定版本、真实字节与哈希、行号及许可文件。相关性仍是可检查的线索，不等于自动证明讲解正确。来源代码默认为未运行。许可未知时隐藏代码正文并保留原因。

本地模型与 GitHub 联网分别授权。默认绑定本机，读取文档的副本，第三方代码只静态读取。模型输出错误、网络失败或无匹配源码会明确显示；无静默云回退。个人笔记和模型权重不进入 Git。

## 开发与交付

```sh
ruff check .
pytest -q
python scripts/tutor.py doctor
python scripts/tutor.py demo
npm --prefix apps/web test
python scripts/package_skill.py
```

`doctor/demo` 保留原来的离线回归；其中 Fixture 的成功不代表真实模型效果。旧 `/api/sprint-1` 与旧笔记接口保留；当前工作台使用 `/api/learning/v1`。

[最终审核与成员贡献](docs/delivery/lead/FINAL_REVIEW.md) · [启动说明](docs/full-delivery/RUNNING.md) · [Skill](SKILL.md) · [完整接口](docs/full-delivery/INTERFACES.md) · [DGX 部署包](deploy/dgx/README.md) · [产品范围](docs/product-scope.md)

只有 @suiyisuixing 最终人工审核和合并。成员原始提交记录保留；CI 和 Codex 审核不能代替人工决定。私有仓库、历史标签和旧个人数据保持原有归属。
