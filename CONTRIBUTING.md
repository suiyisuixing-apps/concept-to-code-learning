# 团队协作

先接受私有仓库 Write 邀请，启用个人 GitHub 2FA，再克隆仓库。不要共享密码、Token 或 SSH 私钥。账号职责见 docs/roles-and-ownership.md；等待邀请的角色标签不等于真实 Assignee。

使用 Python 3.12 和 Node 20.19+，执行 README 的安装、ruff、pytest、doctor、demo、npm test/build。首次入队提交一个不改变产品逻辑的小型文档 PR，由另一位队员审核；合并后删除自己的功能分支。新工作从最新 main 建个人功能分支。

main 要求至少 1 个其他成员批准，phase0-checks 必须成功且分支保持最新，管理员同样受约束。禁止直接绕过评审、关闭保护、force push、历史改写和未经批准的 Release。Phase 0.5 使用 rescope/concept-to-code-learning 分支，v0.2 标签只能在正常审核合并后创建。

一个 PR 应说明具体行为、边界、来源/运行证据、关联 Issue、检查命令和结果。所有新能力区分已实现、Fixture 和未实现；真实解析不改原文件，检索遵循用户授权，来源必须固定 Commit，保存不能覆盖用户笔记。

CI 只有一个 Ubuntu job，最长 10 分钟，push main 与 PR main 触发，同分支取消旧 run。无 schedule、大模型、私有数据、付费 runner、Codespaces、LFS 或付费服务。
