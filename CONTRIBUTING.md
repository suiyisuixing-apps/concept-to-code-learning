# 协作规则

仅本轮用户明确授权的首次初始化提交可直接推送 `main`。此后禁止直接在 main 开发：

1. 每项功能使用 `feature/<issue-number>-<short-name>` 分支。
2. 所有修改通过 Pull Request，关联 Issue、角色和 Milestone。
3. 至少一名其他已授权成员审核；作者不能替代另一位审核人。
4. 合并前通过 ruff、pytest、doctor、demo，以及远程 `phase0-checks` 检查。
5. 禁止 force push，禁止删除 main；只有 Lead 在满足审核条件后执行最终合并。
6. 禁止提交密钥、模型、大型数据、学校课程或企业资料、其他私有仓库实现代码。
7. 公共 Schema 变更由 Lead 协调，增加跨模块兼容样例并更新文档。

GitHub 保护规则仅在现有零费用权益支持时设置。若平台拒绝并要求付费，记录
`BLOCKED_BY_PLAN`，以上规则由团队人工执行；不试用、不升级、不绕过。
CODEOWNERS 不是审核完成证明；其他成员用户名未确认前不能完成双人审核。

## 费用和 CI

CI 仅对 main 的 push / pull_request 运行一个 Ubuntu Job，上限 10 分钟，取消同分支旧任务。
禁止 schedule、多系统矩阵、模型或数据下载、网络测试、大型产物、自动发布和 Release。
不使用 Codespaces、LFS、Packages 或付费 Marketplace App。使用现有免费 Actions 额度；
额度耗尽则保留本地验收并停止远程执行，不购买额度，不修改零美元停止用量预算。

## Pull Request 证据

写明触发场景、行为变化、相关测试和剩余限制。执行输出需要真实退出码；
Fixture 结果必须保留 `FIXTURE` / `SCAFFOLD_DEMO` 标识。
语义映射、代码存在、示例运行、测试通过、教学效果分别记录，不能互相替代。
