# 公开项目与四人共同维护

决策日期：2026-09-21（Asia/Shanghai）。@suiyisuixing 明确授权项目公开，并赋予三名组员完整的仓库权限。本政策取代 2026-09-09 的 Lead 单一负责制；旧记录保留作历史证据。

## 仓库与权限

当前仓库：[suiyisuixing-apps/concept-to-code-learning](https://github.com/suiyisuixing-apps/concept-to-code-learning)。仓库 ID 1360182264，visibility=public。项目从个人账号迁入既有组织，以支持多位仓库管理员；原账号地址由 GitHub 重定向。

| 账号 | 本仓库角色 | 状态 |
| --- | --- | --- |
| @suiyisuixing | Admin | 已生效 |
| @inogi-sama | Admin | 已生效 |
| @zchzbjklg | Admin | 已生效 |
| @fqf060420 | Admin | 已生效 |

三名成员保留为组织外部协作者，获得本仓库 Admin，未授予组织 Owner 或其他仓库访问权。Admin 可以管理本仓库代码、Issues、PR、设置和协作者。任何人均可阅读与克隆公开仓库，公众不会因此获得写入权限。代码公开不改变已有许可条款，也不授权提交个人笔记、密钥、私有材料或模型权重。

## 审核与合并

四位维护者均可审核、提出修改意见和合并通过检查的 PR，包括自己的 PR。无需等待队长单独批准，也不新增强制互审。原模块分工是协作联系人安排，不是排他权限；公共合同修改与受影响维护者协调并提供兼容性证据。

保留 Issue、功能分支、聚焦 PR 和验证。合并前阅读已有反馈、确认当前 Head 的 required CI、处理已知 P0/P1，并准确区分真实能力、Fixture 和未实现。人工检查、Codex 审计、CI 成功、正式 Review 和已合并是不同状态，不能互相替代。权限开放本身不授权代理合并所有存量 PR。

旧 lead-review:*、owner-merge-only 标签及旧任务书的 Lead-only/private 条款不再构成当前权限限制。历史记录不删除，新 PR 使用当前模板。

## main 保护与核验

2026-09-21 通过 GitHub API 回读确认：

- Ruleset 22609095 更名为 main-team-maintained，Active，覆盖 main 和默认分支。
- 移除专属更新限制，bypass_actors 为空；保留 PR、phase0-checks、禁止删除及强推。
- Required approvals 为 0；未启用 Code Owner、最后推送者之外的批准或强制讨论解决门禁。
- phase0-checks 绑定 GitHub Actions（15368），严格要求最新 main；Classic Protection 的 enforce_admins=true。
- 四人均为 Admin，无待接受的仓库邀请。
- 仓库 ID、迁移前的 19 个分支 Head 和 7 个开放 PR 的编号、Head、目标分支均保留；迁移未合并这些 PR。

[配置快照](main-protection.json)与自动化测试只证明已记录的配置约束，不证明未来实时设置。复核时查看仓库 Settings → Collaborators、Rulesets 和 Branches，或读取 GitHub API 的 collaborators、invitations、rulesets/22609095、branches/main/protection。没有通过他人账号冒充操作或进行破坏性推送测试。

普通开发不直接 Push main、不绕过失败 CI、不强推、不删除 main、不改写历史或移动旧标签，也不为方便合并而关闭保护。后续维护者如需调整治理，应记录明确决定、复核影响并回读设置。维持零新付费与现有有界 CI。

## 已有克隆

```sh
git remote set-url origin https://github.com/suiyisuixing-apps/concept-to-code-learning.git
```

原 PR、Issue、贡献和标签记录随仓库保留；迁移不会把尚未合并的功能自动带入 main。
