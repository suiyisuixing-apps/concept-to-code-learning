# Concept-to-Code Onboarding

把培训材料中的知识点映射到真实代码，并以运行和测试形成学习证据。

**版本：0.1.0.dev0 · Phase 0 · 赛前工程原型**

当前可用：项目检查、四个 JSON Schema、固定合成资料的来源定位、Python AST
函数验证、实际示例运行和 pytest，以及三份演示产物。当前未实现：PPTX/DOCX/PDF
自动解析、本地模型调用、智能映射、项目练习生成/评分和漂移检测。

## 本地运行

使用 Python 3.12，在仓库根目录执行：

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
ruff check .
pytest -q
python scripts/tutor.py doctor
python scripts/tutor.py demo
```

安装后也可使用 `concept-to-code doctor` / `concept-to-code demo`，工作目录仍须为本仓库。
运行过程不需要模型、服务器、云账号或网络；首次安装仅从 Python 包索引获取轻量依赖。
`jsonschema` 是唯一运行时依赖，用于实际校验团队接口；开发依赖为 pytest、ruff、PyYAML。

演示输出位于 `reports/demo/`（Git 忽略）：

- `concept-code-map.json`：概念、来源、真实函数与测试位置。
- `guided-lesson.md`：与示例函数对应的讲解。
- `learning-evidence.json`：输入哈希、实际执行命令、退出码和结果。

三份结果均标注 `mode: FIXTURE`、`status: SCAFFOLD_DEMO`。
示例只有 FastAPI 风格的普通 Python 服务函数，不依赖 FastAPI，也不启动 HTTP 服务。
临时目录只用于固定可信 Fixture；它不是任意企业代码的安全沙箱。

## 开发入口

先阅读 [SKILL.md](SKILL.md)、[产品范围](docs/product-scope.md)、
[公共接口](docs/data-contracts.md)、[角色分工](docs/roles-and-ownership.md) 和
[协作规则](CONTRIBUTING.md)。四角色通过 Schema 协作；待实现模块有明确边界。

- [里程碑](https://github.com/suiyisuixing/concept-to-code-onboarding/milestones)
- [任务列表](https://github.com/suiyisuixing/concept-to-code-onboarding/issues)
- [路线图](docs/roadmap.md) · [看板手动配置](docs/project-board-manual-setup.md)
- [借鉴登记](docs/reuse-ledger.md) · [比赛假设](docs/competition-assumptions.md)

仓库保持 Private；没有开源 LICENSE，也没有 GitHub Release。比赛资格和知识产权规则
尚未提供官方文件，`pre-rules-v0.1.0` 只标记赛前工程基础。
