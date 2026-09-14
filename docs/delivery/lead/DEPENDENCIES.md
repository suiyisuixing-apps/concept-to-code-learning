# 依赖与许可观察 · 2026-09-14

当前运行基线为 Python 3.12、Node 22.13+。安装使用 `requirements/full-delivery-py312.lock` 与 `apps/web/package-lock.json`。前端为 React 19.2.0、Vitest 4.1.11、PDF.js 6.3.289；历史文档中的 Node 20、Vitest 3 和 28 包清单不再描述当前候选。

[dependencies.json](dependencies.json) 覆盖 Python 约束文件的全部 35 项：34 项来自本机已安装 distribution 的 METADATA，额外一项为 Windows 条件依赖 colorama 0.4.6，许可来源单列为 PyPI 发布元数据。它没有被写成本机已安装证据。Pillow 是测试直接使用的包，因此也显式列入 dev 依赖。当前 anyio 4.15.1 的 METADATA 没有 sniffio 依赖，未依据旧版依赖关系添加它。

这个约束文件固定版本和平台条件，不是全平台带下载哈希的锁文件。Windows 安装及用例由标准 Windows CI 检查；CI 不代替实际用户的模型、图形界面或 DGX 验收。

许可字段是包元数据的观察值；未声明时明确保留未知。第三方源码的展示许可仍由来源模块按仓库和固定 Commit 核对，不继承这些包的许可。

2026-09-14 对当前 npm 锁文件执行 `npm audit --json`，退出 0、报告漏洞 0；这只表示该次依赖公告查询结果。[历史 npm 告警](evidence/npm-audit.json) 保留在旧证据中，不再作为当前依赖状态。当前复核与检查范围见 [REVIEW_CORRECTIONS.md](REVIEW_CORRECTIONS.md)。

支持的启动方式仍是完整源码 checkout 中的 `python scripts/desktop.py`；未宣称独立安装 wheel 后不需要仓库资源。
