> 2026-09-21 权限更新：[当前共同维护政策](../governance/team-maintained-policy.md)优先。项目已公开于 `suiyisuixing-apps/concept-to-code-learning`；四人均为仓库 Admin，均可审核和合并通过检查的 PR，无需 Lead 专门批准。模块分工不是文件权限限制；不得绕过 CI，Codex 不代填人工检查。以下旧任务中的私有、仅 Lead 合并和成员 Write 条款已失效，其他功能及证据要求保留。

> 当前范围已由 [完整模块任务书](full-delivery/README.md) 取代；以下保留旧阶段的任务与证据，不作为本轮功能上限。

# AI Tutor / Local Model / Evaluation Codex 工作提示词

适用范围：2026-09-09 起执行 Lead 单一负责制，见 [治理政策](../governance/lead-controlled-merge-policy.md)。下文合同与实现描述对应 PR #58；治理文档本身不引入这些运行时代码，使用前核验 #58 是否已进入 main。

2026-09-08 基线：PR #56 已获 @fqf060420 正式 APPROVED 并由其合并；pre-rules-v0.2.0 固定在 e83a64d63a78f11534fbe51631775ceeb3885ccb。本文及 Sprint 1 合同通过独立 [Lead 准备 PR #58](https://github.com/suiyisuixing/concept-to-code-learning/pull/58) 交付；模块开发前确认该 PR 已由 Lead 完成自检、Codex 审计、required CI 并合并。Lead PR 无需外部批准。

你是 @fqf060420 的 Codex，负责 AI Tutor / Local Model / Evaluation。请实际完成以下聚焦工作与验证，不要只给计划。仓库：https://github.com/suiyisuixing/concept-to-code-learning。本地先检查 /Users/freewill/Documents/GitHub/concept-to-code-learning；若路径不存在，通过当前 Git remote 确认，不能猜测或覆盖其他项目。使用本人 GitHub 账号，不共享凭据。若当前账号不是 @fqf060420，停止 GitHub 写操作，不复制或共享 Token。

指定分支：`feat/grounded-explanation`。前置门禁全部满足后，从已更新 main 创建；已有同名分支先检查归属和状态，不能重置。主 Issue：[49](https://github.com/suiyisuixing/concept-to-code-learning/issues/49)。此外，先确认 Lead 合同准备 PR 已经审核并合并到 main；若尚未合并，只可阅读合同与用本地 Fixture 准备，不私自冻结或改写公共合同。

## 本次目标与范围

实现 GroundedTutorProvider，接收文档上下文和已核验代码，提供 Beginner/University 两档联合解释；建立明确 FixtureProvider、OpenAICompatibleProvider 接口与配置错误处理，补普通聊天对照 Grounded Skill 评测。主 #49，关联 #50/#51；主要路径 tutor/、runtime/、evals/ 与对应测试。

不实现 PPTX/GitHub 客户端或 NoteStore，不部署 DGX、不下载权重、不微调、不新增云账户/付费服务。不能用固定答案伪装模型，不能自动从本地模型失败切到云。

## 输入合同

Lead 已冻结的 DocumentContext、服务端 Verified GitHubCodeSource、question、explanation_level。可先使用全 Fixture 合同并行开发，真实联合验收等待 Document 与 GitHub PR。允许的真实模型仅为用户明确配置授权的本地 OpenAI-compatible endpoint/model；未配置就明确返回状态。

## 输出合同

GroundedExplanation：question、explanation_level、concept、explanation、document_context、document_citations、github_sources、unsupported_claims、unresolved_items、provider_mode，以及兼容所需 ID/模式/运行状态。返回原文与源码可核对的双来源；未经验证来源不得返回有真实代码依据的完成状态；不支持断言必须显式列出。

## 已建立的集成接缝

对接 integration/ports.py 的 GroundedTutorProvider.explain(context, source, question, level)，返回 schemas/sprint-1/grounded-explanation.schema.json。当前 Lead 的 FixtureGroundedTutor 仅支持冻结的 DI 场景；本任务负责两档讲解 Provider 与联合数据适配。文档或来源仍为 Fixture 时总体 mode/status 保持 FIXTURE/SCAFFOLD_DEMO；provider_mode 记录讲解器身份，全部真实且有依据才是 LIVE/GROUNDED_ANSWER。TUTOR_BASE_URL/TUTOR_MODEL 当前只是配置检查，尚未发送任何模型请求。

## 验收标准

两档文本行为可区分而证据一致；空/越界上下文、无源码、UNVERIFIED、无配置、不可达/超时/无效响应都准确失败，无静默 Fixture 或云回退。Fixture 标签和当前 provider_mode 随响应与保存快照保留。对照评测使用相同输入/问题；未实际运行真实模型时只交付评测壳/Fixture，不能发布伪真实模型分数。

本地 Adapter 接缝为未来 DGX 留入口；本期以正确合同和可信错误为先，不因硬件缺失阻塞全 Fixture 测试。

## 共同工作规则

先读取仓库 AGENTS.md、docs/sprint-1-first-real-vertical-slice.md、docs/sprint-1-contract-review.md、当前 API/Schema/测试与对应 Issue。若文件或合同尚未通过 Lead PR 冻结，报告 BLOCKED，不能猜测未合并版本的接口已在 main 生效。

核对 gh 当前账号、origin、分支和工作树；不得覆盖他人的未提交改动。核验 main 包含已合并的历史基线 pre-rules-v0.2.0。PR #56 的既有审批只是历史事实，不要求队员重新批准。共同合同是否生效取决于 Lead 合并记录；普通评论、标签、CI 和正式 Review 必须分别报告。

始终维持私有与零新付费；不购买/试用服务，不提交模型、Key、Token、真实学校/企业资料、其他私有仓库或完整外部仓库。文档和来源仓库只读；最小引用并保留许可；不得编造仓库、Commit、路径、符号、行号或许可证。搜索结果不是 Verified。Fixture/Mock/固定文本必须可见标记。无自动云回退；任何实际联网必须在用户明确授权的具体来源/本地模型范围内。

禁止直接推 main，禁止强推、reset --hard、改写历史或移动已有正式标签。一个分支/PR 只处理一个聚焦问题。未经 Lead 批准不得擅自修改公共 Schema；有冲突先写清最小变更原因，不私建另一套不兼容合同。成员不得合并自己或他人的 PR，不得启用 Auto-merge、Queue merge、Admin bypass 或修改 Branch Protection/Ruleset；不要替其他角色实现完整模块。不要自动启动其他成员的 Codex 任务。

## 必跑验证

使用 Python 3.12 的项目虚拟环境；前端使用 CI 对齐的 Node 20。记录每条命令、退出码、通过/失败数、耗时与作用范围。

```sh
python -m pip install -e ".[dev]"
ruff check .
pytest -q
python scripts/tutor.py doctor
python scripts/tutor.py demo
npm --prefix apps/web ci
npm --prefix apps/web test
npm --prefix apps/web run build
```

每个行为变化补对应正向和失败路径测试，使用临时数据目录，不改现有个人笔记。默认 DOCUMENT_PROVIDER=fixture、GITHUB_SOURCE_PROVIDER=fixture、TUTOR_PROVIDER=fixture；CI 不联网、不下载模型、不增加付费 Runner。实际真实 Provider 验收另行 opt-in，记录实际命令与来源证据，不把 Mock 当成 live。未执行为 NOT_ATTEMPTED，不得声称通过。

## PR 与交付

先提交到指定个人分支，推送后创建指向 main 的聚焦 PR，关联主 Issue，正文写行为、接口/兼容边界、失败路径、测试数量/命令与真实/Fixture 区别。提交时标记 lead-review:pending，等待 @suiyisuixing 最终审核，核验远程当前 head 的 phase0-checks；成员不得合并任何 PR。可以对 Lead PR 提非阻塞 Comment 建议；不得绕过 CI。

最终用中文输出 DONE/PARTIAL/BLOCKED/FAILED/NOT_ATTEMPTED：实际修改、Commit、PR URL、当前 head CI、新增测试数、未完成能力及后续依赖；不能用“接口存在”替代真实能力完成。
