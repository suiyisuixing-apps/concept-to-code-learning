# 团队协作

项目现为公开仓库：[suiyisuixing-apps/concept-to-code-learning](https://github.com/suiyisuixing-apps/concept-to-code-learning)。任何人可以阅读和克隆；@suiyisuixing、@inogi-sama、@zchzbjklg、@fqf060420 四人均拥有本仓库 Admin 权限，三名成员的权限已经生效，无待接受邀请。使用各自 GitHub 账号并启用 2FA，不共享密码、Token 或 SSH 私钥。

四人共同维护代码、Issues、PR、设置和协作者，均可审核和合并满足条件的 PR，包括自己的 PR，无需队长专门批准。原模块分工用于协作衔接，不是文件访问限制。仓库 Admin 不等于组织 Owner，也不授予其他仓库的访问权。详见[共同维护政策](docs/governance/team-maintained-policy.md)与[模块联系人](docs/roles-and-ownership.md)。

所有改动使用 Issue → 最新 main 上的功能分支 → 聚焦 PR → 本地验证与 required CI → 维护者审核决定。一个 PR 关联一个主要 Issue。阅读已有建议，解决已知 P0/P1 问题，区分真实能力、Fixture 和未实现；不要把普通评论、自动审计、标签或绿色 CI 冒充正式 Review 或人工检查。Codex 不能代填人工检查。

main 必须通过 PR 更新，phase0-checks 必须成功且分支基于最新 main；外部 required approval count 为 0。2026-09-21 已通过 API 回读 main-team-maintained Ruleset：无人员专属更新限制，无绕过名单；保留 PR、required CI、禁止强推及删除。Classic Protection 的 enforce_admins=true。管理员也遵循这些保护，不直接 Push main、不绕过失败 CI、不改写历史，不在普通开发中开启自动合并或降低保护。配置快照不是实时权限证明，操作前按需回读。

每个 PR 写明行为变化、关联 Issue、当前 Head、来源/运行证据、实际命令及退出码。公共 Schema 变更与受影响模块维护者协调，附兼容性与回归证据。旧 lead-review 与 owner-merge-only 标签保留作历史记录，不再要求新 PR 使用，也不构成合并权限门禁。

使用 Python 3.12 和 Node 22.13+，按 README 执行适用的安装、ruff、pytest、doctor、demo、npm ci/test/build。测试使用临时数据目录；纯文档修改运行相关检查即可。真实解析不改原文件，检索遵循授权，来源固定 Commit，保存不能覆盖用户笔记。

CI 保留现有 Ubuntu 和 Windows job，各最长 10 分钟，push main 与 PR main 触发，同分支取消旧 run。维持零新付费，不购买/试用服务，不新增付费 runner 或后台 schedule。公开的是项目代码和已有仓库历史；个人笔记、密钥、模型权重、私有资料及外部仓库副本不得提交。历史标签和成员贡献记录保留。

旧地址仍可用于 GitHub 重定向；已有克隆建议更新 remote：

```sh
git remote set-url origin https://github.com/suiyisuixing-apps/concept-to-code-learning.git
```
