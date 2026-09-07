# 四人职责与入队状态

2026-09-07 API 已验证四个确切账号。三名队员收到普通 Write 邀请；@fqf060420 已接受，其余两名仍待接受。待邀请角色是明确主责，但未设置虚假 Assignee。CODEOWNERS 用户名真实、路径实际存在；待邀请成员接受前对应自动评审能力尚不可用；@fqf060420 已可实际参与评审。

| 账号 | 角色 | 主责 Issues（含历史关闭） | 真实 Assignee |
| --- | --- | --- | --- |
| @suiyisuixing | Lead / Product / Skill / Integration | #1, #2, #3, #4, #5, #6, #31, #35, #36, #37, #38, #52 | 已分配 @suiyisuixing |
| @inogi-sama | Document Workspace / Frontend | #7, #8, #9, #14, #29, #39, #40, #41, #42, #53 | 等待邀请接受 |
| @fqf060420 | AI Tutor / Local Model / Evaluation | #10, #11, #12, #13, #23, #24, #25, #26, #27, #28, #30, #33, #49, #50, #51, #55 | 已分配 @fqf060420（开放任务；历史关闭任务未重新分配） |
| @zchzbjklg | GitHub Code Intelligence | #15, #16, #17, #18, #19, #20, #21, #22, #32, #34, #43, #44, #45, #46, #47, #48, #54 | 等待邀请接受 |

## 未来 48 小时

先完成 #53/#54/#55 入队验收。首次功能实现从个人分支提交，来源/UI/模型分别在已定义接缝工作，公共契约由 Lead 协调。

### @suiyisuixing

1. 冻结 Product、Skill 和 API 合同。
2. 集成 Document → Tutor → GitHub Evidence → Note 纵向切片。
3. 审核 Issue 迁移。
4. 管理 PR 和受保护 main。

### @inogi-sama

1. 完成三栏 React 页面。
2. 完成 PPTX 当前 Slide 最小读取。
3. 完成当前页面与选区状态。
4. 完成保存笔记 UI。
5. 提交至少一个功能 PR。

### @zchzbjklg

1. 实现用户指定公开仓库模式。
2. 固定一个真实仓库 Commit。
3. 验证文件、符号和行号。
4. 生成第一张真实代码来源卡。
5. 提交至少一个功能 PR。

### @fqf060420

1. 实现 Document Context → Concept → Grounded Explanation。
2. 实现 Beginner 和 University 两种解释。
3. 建立本地 OpenAI-compatible Adapter 接口。
4. 建立普通聊天与 Grounded Skill 对照测试。
5. 提交至少一个功能 PR。

## 审核与接受后的分配

只有 GitHub API 确认成员已接受并拥有 Write 后，才将对应开放 Issues 设置为该用户 Assignee，并移除 waiting-for-collaborator。首选 Reviewer @inogi-sama，其次 @zchzbjklg、@fqf060420；未接受不能请求审核。账号本人完成 2FA，无须共享安全码。
