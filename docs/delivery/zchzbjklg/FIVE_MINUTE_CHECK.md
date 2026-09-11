# 来源模块复验

PR #73 的原始提交为 `1fc4b7d6334f16cf783e1db75e443d6007af6f78`，
基线为 `9f9b8d1e62f0d7cbbd0a86c4fe93f25e5daaae94`。原提交新增 20 项离线测试；
Lead 集成补齐后，失败矩阵共有 24 项。当前结果见 [Lead 审核记录](../lead/PR73_REVIEW.md)。

## 环境

在仓库根目录使用 Python 3.12 的项目虚拟环境。Windows 用 `.venv/Scripts/python.exe`，
macOS/Linux 用 `.venv/bin/python`。项目不要求固定在 3.12.10，也不需要永久设置 `PYTHONUTF8`。

```sh
python -m pip install -c requirements/full-delivery-py312.lock -e ".[dev]"
```

这里的 `python` 应指向上述虚拟环境。锁文件及 `pyproject.toml` 已包含文档解析依赖；
缺依赖时先对齐本机环境，不能把失败列为正常验收结果。

使用独立临时 HOME、数据和测试目录，不把个人课件或笔记用作测试输入。

## 差异核对

用固定提交比较原始贡献，合入后仍可复验；不要与会继续移动的远程分支比较：

```sh
git diff --stat 9f9b8d1e62f0d7cbbd0a86c4fe93f25e5daaae94 1fc4b7d6334f16cf783e1db75e443d6007af6f78
git diff --name-only 9f9b8d1e62f0d7cbbd0a86c4fe93f25e5daaae94 1fc4b7d6334f16cf783e1db75e443d6007af6f78 -- src/ schemas/ .github/ pyproject.toml apps/web/
```

第二条应无输出。Lead 补丁也只修改测试与说明。

## 检查

```sh
python -m ruff check .
python -m pytest tests/github_intelligence/test_source_failure_matrix.py -q
python -m pytest tests/github_intelligence -q
python -m pytest -q
python scripts/tutor.py doctor
python scripts/tutor.py demo
```

完整环境的要求是全部执行通过；操作系统不支持创建符号链接时，现有该项测试可以按代码中
的明确原因跳过。不得忽略其他失败。`doctor` 应为 `DONE`、6 个 Schema、无错误；
`demo` 应明确返回 `FIXTURE / SCAFFOLD_DEMO`，它不是实际模型验收。

重点检查：公开搜索在仓库发现、树读取和文件读取时取消，均传播取消；即使已有候选也不返回
部分结果。读取响应头或半截响应体时取消，缓存不留下临时或完整文件，重新读取才写入完整响应。

成员报告的 Windows 沙箱删除拦截是历史环境记录，Lead 无原始完整日志，不能把它写成当前
必然原因。若复现，保留失败日志并使用新的独立临时目录；不要删除已有个人数据或绕过守卫。

## CI 与真实能力

PR #73 目标是集成分支，现有 CI 只对目标为 `main` 的 PR 执行。整合版本由 Draft PR #69
的 Linux/Windows CI 核验，不更改触发条件来制造通过状态。

这些 HTTP 故障测试使用替身；真实静态 Git/文件读取使用自制临时仓库。合成 FastAPI 形状
的样例并非从标注的 commit 下载的真实源码，MIT 文本也是合成测试输入。既有真实代码与
模型验收另见 [CONTEXTUAL_SEARCH.md](../lead/CONTEXTUAL_SEARCH.md)。
