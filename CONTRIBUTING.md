# 团队协作

先接受私有仓库 Write 邀请，启用个人 GitHub 2FA，再克隆仓库。不要共享密码、Token 或 SSH 私钥。账号职责见 docs/roles-and-ownership.md。

所有工作使用 Issue → 最新 main 上的功能分支 → 聚焦 PR → 本地验证与 required CI → Lead 决定。一个 Issue 对应一个聚焦 PR。首次入队提交不改变产品逻辑的文档 PR，由 Lead 审核；合并后可删除自己的功能分支。

@suiyisuixing 是唯一最终审核人和唯一 main 合并人。成员 PR 等待 Lead 审核、退回或合并；成员不得合并自己或他人的 PR，不得启用 auto-merge、merge queue 或管理员例外。Lead 自己的 PR 无需外部批准，在 Lead 人工自检、Codex 独立差异审计、required CI 成功、没有 P0/P1 阻塞且能力声明准确后可以自行合并。Codex 辅助检查，最终决定属于 Lead，不能代填人工检查。

组员可通过 Comment 或普通 Comment Review 提出非阻塞建议；Lead 合并前阅读已有建议并决定是否采纳。不得把普通评论、自动审计、标签或绿色 CI 冒充正式 Review。

main 必须通过 PR 更新，phase0-checks 必须成功且分支基于最新 main；外部 required approval count 为 0。禁止直接 Push main、Force Push、历史改写、删除 main、绕过 CI 或未经授权修改保护。2026-09-09 已核验 Active main-lead-controlled Ruleset：Restrict updates，仅 Repository administrators 可通过 PR 使用例外；Classic Protection 保留 PR、required CI 与 enforce_admins=true。三名成员为 Write，唯一 Admin 为 @suiyisuixing。后续操作仍需核验实时设置，详见 docs/governance/lead-controlled-merge-policy.md。

每个 PR 填写具体行为、边界、来源/运行证据、Issue、角色及真实命令和退出码。新成员 PR 创建时标记 lead-review:pending；Lead 接收时补齐标签，确认后更新决定标签。标签不代替 CI，也不自动授予合并权。不增加标签专用 CI 或后台付费任务。

使用 Python 3.12 和 Node 20.19+，执行 README 的安装、ruff、pytest、doctor、demo、npm ci/test/build。测试使用临时数据目录。所有新能力区分已实现、Fixture 和未实现；真实解析不改原文件，检索遵循用户授权，来源固定 Commit，保存不能覆盖用户笔记；公共 Schema 变更先获 Lead 批准。

CI 保留一个 Ubuntu job，最长 10 分钟，push main 与 PR main 触发，同分支取消旧 run。仓库保持私有与零新付费；不购买/试用服务，不增加付费 runner、Codespaces、LFS、schedule、大模型或私有数据。本次不创建 Release 或新 Tag，不移动历史标签。
