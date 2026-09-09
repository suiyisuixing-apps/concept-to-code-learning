# Lead 单一负责制与 main 合并政策

决策日期：2026-09-09（Asia/Shanghai）。决策人及唯一最终负责人：@suiyisuixing。成员：@inogi-sama、@zchzbjklg、@fqf060420。

## 决策与责任

原流程要求另一名成员批准，且禁止作者合并自己的 Sprint PR；这一规则保留在历史 PR/Issue 记录中。新流程取消强制互审，以减少等待并把最终质量、范围、公共 Schema、来源、发布声明与合并责任明确交给 Lead。成员开发、提交聚焦 PR、响应修改要求，可提供非阻塞建议；不得合并任何进入 main 的 PR。

所有改动仍通过 Issue、功能分支、PR 和强制 CI。成员 PR：功能与测试完成 → required CI 成功 → Lead 最终审核 → Lead 合并。Lead PR：功能与测试完成 → required CI 成功 → Codex 只读差异审计 → Lead 人工检查关键文件、阅读已有建议 → 无 P0/P1 且声明准确 → Lead 自行合并，无需外部批准。

Codex 不能替代人的最终决定。Lead 自检真实完成后才记录 LEAD_SELF_REVIEW_PASSED。机器审计可以记录 CODEX_AUDIT_PASSED；它不等于人工自检、正式 Review 或已合并。Lead 可以对成员 PR 使用 Approve、Request changes 或 Comment；组员对 Lead 默认使用 Comment/Comment Review。

## 已核验的 GitHub 配置

2026-09-09 通过 Owner gh 凭据创建并回读 [main-lead-controlled](https://github.com/suiyisuixing/concept-to-code-learning/rules/22609095)，ID 22609095，Active，匹配 refs/heads/main 和默认分支。API 配置证据结论：ENFORCED；没有通过组员账号做破坏性 Push/Merge 探测。操作前仍须实时回读，文件不是实时控制面。

| 层 | 设置 | 作用 |
| --- | --- | --- |
| Ruleset | Restrict updates；唯一例外 Repository administrators，pull_request 模式 | Write 成员不能更新 main；管理员只可经 PR 更新 |
| Ruleset | Restrict deletions、non_fast_forward | 禁止删除/强推 main |
| Ruleset | PR 必须；approvals 0；Code Owner/last-push/stale/thread resolution false | 取消强制互审，保留 PR |
| Ruleset | phase0-checks，GitHub Actions app 15368，strict=true | 要求最新 main 上的检查 |
| Classic Protection | PR 对象保留，approvals 0；上述 review 附加开关均 false | 继续要求 PR，不设置 PR bypass allowances |
| Classic Protection | phase0-checks/app 15368、strict=true、enforce_admins=true | 管理员也必须通过 PR 与 CI，不能借 Ruleset 的例外跳过此层 |
| Classic Protection | force push=false，deletion=false | 禁止强推和删除 main |

Ruleset 的管理员例外作用于该 Ruleset 的规则，所以必须保留独立 Classic PR/CI 与 enforce_admins。不要只设置带管理员例外的单一 Ruleset 后声称 CI 无法绕过。GitHub 对同时匹配的 Ruleset 和 Classic 规则共同执行。当前唯一 Admin 为 @suiyisuixing；三名成员均保留 Write，无 Maintain/Admin。任何后续新增管理员都会改变“只有 Lead”的前提，须由 Lead 复核。

配置声明位于 main-protection.json；本地测试仅验证声明和文档，不伪装成远程控制验证。本次远程读取与更新回执单独保存在治理迁移报告的证据目录。

## 保留与取消的门

保留：PR、phase0-checks、最新 main、Lead 人工决策、无 P0/P1、Fixture/真实/未实现区分、源文件只读、固定 SHA/路径/符号/行/许可核验、显式保存不可变笔记、私有仓库与零新付费。禁止直接 Push main、强推、历史改写、删除 main、绕过 CI、自动云回退、提交密钥/模型/私有文档/外部仓库副本。

取消：强制其他成员批准、Code Owner Review、最后一次 Push 的他人批准、stale approval dismissal、强制解决讨论。公共 Schema 仍需 Lead 批准。取消 GitHub 讨论门禁不意味着可以忽略已知 P0/P1。

## 标签与建议

成员创建 PR 时添加 lead-review:pending；Lead 接收时补齐。Lead 确认决定后只保留一个对应标签：lead-review:approved、lead-review:changes-requested、lead-review:deferred。建议使用 team-suggestion；相关 PR 添加 ci-required 与 owner-merge-only。标签是项目记录，不能赋予合并权或替代 required CI。PR 模板默认 LEAD_REVIEW_PENDING；没有新增后台标签任务或付费服务。

## 网页复核及失效时处理

打开仓库 Settings → Rules → Rulesets → main-lead-controlled，确认 Active、Default branch/main、Restrict updates/deletions、Block force pushes、PR required、approvals 0、phase0-checks、Repository administrators / For pull requests only。关闭 Code Owner、last push、stale approvals、conversation resolution。

再到 Settings → Branches → main 的 Classic protection，保留 Require a pull request、required status checks/phase0-checks、Require branches to be up to date、Do not allow bypassing the above settings（enforce_admins），approvals 0，无 PR bypass allowances，禁止强推与删除。

若 Ruleset 不可用，保留 Classic PR/CI 和 approvals 0，标记 POLICY_ONLY_NOT_TECHNICALLY_ENFORCED、OWNER_ONLY_MERGE_NOT_ENFORCED，并明确 Write 成员技术上仍可能合并。不能靠文档宣称技术强制，不能为此购买/试用服务。当前 API 配置已成功回读，无需用户补做网页设置。

## 回滚

由 Lead 记录新决策，通过独立聚焦 PR 恢复文档，先在 Classic 恢复 required approving reviews=1 和原 stale 设置，保留 PR/CI、enforce_admins、强推/删除禁令；回读确认后才考虑调整 owner-only Ruleset。不得先删除保护制造无保护窗口，不移动旧 Tag，不创建 Release。若仅文档回滚而远程设置未改，应明确两者差异。

## 成本和证据

本次未购买、升级、开通试用或添加付费服务，CI 继续原有一个 Ubuntu job、10 分钟上限与同分支取消。账户账单/剩余 Actions 配额未由本次 API 证明，不能据此声称历史账单为零。治理配置、评论和文档不使用新的收费服务；保持零新增付费约束。

依据：[GitHub Rulesets 的分层执行](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/about-rulesets)、[PR-only bypass](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/creating-rulesets-for-a-repository)、[Branch Protection API](https://docs.github.com/en/rest/branches/branch-protection)。
