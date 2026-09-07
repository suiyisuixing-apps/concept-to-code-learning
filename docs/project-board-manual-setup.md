# Project 看板手动配置

状态：`PROJECT_BOARD_BLOCKED`。2026-09-07 实际执行 `gh project create`，CLI 返回
缺少 `project` 和 `read:project` OAuth scopes；没有创建 Project，也没有 Project URL。
保留全部 36 个 Issues、6 个 Milestones 和角色标签，不反复尝试，不启用付费服务。

账号本人可在现有 GitHub 网页中完成以下免费配置；无需新增订阅：

1. 个人账号 suiyisuixing → Projects → New project → Board。
2. 名称设为 `Concept-to-Code Onboarding – DGX Spark Hackathon`，可见性保持 Private。
3. Status 选项设为 Backlog、Ready、In Progress、Review、Blocked、Done。
4. 从 `suiyisuixing/concept-to-code-onboarding` 加入 #1–#36，核对共 36 项。
5. 已经有验收证据且关闭的 Issue 设 Done；依赖齐备设 Ready，其余 Backlog。
6. 将 Project 与本仓库关联，把实际 URL 写回本文件。

若改用 CLI，只有账号本人决定并完成 `project` 授权后才能重试；本轮没有扩大凭据权限。
看板未建不影响通过 Issues、Milestones、Role Labels 跟踪工作。
