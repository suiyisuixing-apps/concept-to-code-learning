# 依赖注入学习 Fixture

mode: FIXTURE
status: SCAFFOLD_DEMO

`document.json` 是本项目人工编写的合成中文讲义，不含真实课件。`github-source.json` 引用公开 FastAPI 仓库的一条冻结原始代码，不是虚构仓库：

- 仓库：https://github.com/fastapi/fastapi
- Commit：50113da16fec53b66b80d75e80a89296de4fa5a5
- 文件：docs_src/dependencies/tutorial001_an_py310.py
- 符号：read_items；AST 类型 AsyncFunctionDef；含装饰器的原文 12–14 行。
- 链接：https://github.com/fastapi/fastapi/blob/50113da16fec53b66b80d75e80a89296de4fa5a5/docs_src/dependencies/tutorial001_an_py310.py#L12-L14
- 验证：2026-09-07 GitHub API 仓库、Commit、固定文件 blob；Python AST 定位、行范围和片段 hash；同 Commit LICENSE 为 MIT。
- 最小引用仅三行；许可证与版权通知保存在 FASTAPI-LICENSE.txt，未复制完整仓库。
- 状态：GITHUB_SOURCE_VERIFIED（本次冻结核验）；NOT_RUN（未执行此片段）。

四档解释为人工固定文本。UI 与服务不会重新访问 GitHub，也没有通用 verifier。改变冻结来源必须在新的 PR 中重新核验，不能仅改 status。解释与个人笔记分开，只有用户按钮保存才新增本地笔记。
