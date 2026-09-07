# 四人分工

| 角色 / Label | GitHub 用户名 | 负责模块 | 第一批 Issue | 当前里程碑 |
| --- | --- | --- | --- | --- |
| Lead / role:lead | @suiyisuixing | SKILL、范围、Schema、CLI、集成、来源、合并、演示 | #1–4，#31 | M0 |
| Documents / role:documents-model | 待用户提供 | PPTX/DOCX/PDF、来源、概念、本地模型、DGX、文档评测 | #7、#8、#14 | M1 |
| Code Intelligence / role:code-intelligence | 待用户提供 | Python AST、路由配置、测试映射、验证、隔离执行、漂移 | #15、#18 | M2 |
| Teaching / role:learning-evaluation | 待用户提供 | 讲解、示例包装、练习、隐藏测试、学习证据、对照评测、视频 | #23、#25、#26 | M3 |

主责 Issue 数量：Lead 9，Documents 8，Code Intelligence 10，Teaching 9。
共享任务单一主责：#31 Lead、#32 Code Intelligence、#33 Teaching、#34 Code Intelligence、
#35 Lead、#36 Lead；其他角色通过依赖配合。仅 Lead 任务分配给现有账号，其他只加角色标签。

未确认另外三名队员用户名，不邀请任何账号。账号确认并接受仓库邀请后才能克隆私有仓库、
承担具体 Issue 和完成双人 PR 审核；届时再更新本表和 CODEOWNERS。

## 最先 48 小时

- Lead：核对四个 Schema 与模块样例；协调 #31 的一个概念纵向切片及 PR 审核。
- Documents：完成带页码的 PPTX 最小解析；完成带章节/段落的 DOCX 最小解析。
  同步明确 #12 的本地模型接口；运行时实现仍按 M5 排期。
- Code Intelligence：完成 Python AST 索引；让真实/不存在的符号分别获得明确核验结果。
- Teaching：准备第一个知识点讲解和限界练习；准备正确版、错误版和隐藏测试。
