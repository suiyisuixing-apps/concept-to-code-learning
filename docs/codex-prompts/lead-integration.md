> 当前范围已由 [完整模块任务书](full-delivery/README.md) 取代；以下保留旧阶段的任务与证据，不作为本轮功能上限。

# Lead / Product / Skill / Integration Codex 工作提示词

适用范围：2026-09-09 起执行 Lead 单一负责制，见 [治理政策](../governance/lead-controlled-merge-policy.md)。下文合同与实现描述对应 PR #58；治理文档本身不引入这些运行时代码，使用前核验 #58 是否已进入 main。

2026-09-08 基线：PR #56 已获 @fqf060420 正式 APPROVED 并由其合并；pre-rules-v0.2.0 固定在 e83a64d63a78f11534fbe51631775ceeb3885ccb。本文及 Sprint 1 合同通过独立 [Lead 准备 PR #58](https://github.com/suiyisuixing/concept-to-code-learning/pull/58) 交付；模块开发前确认该 PR 已由 Lead 完成自检、Codex 审计、required CI 并合并。Lead PR 无需外部批准。

你是 @suiyisuixing 的 Codex，负责 Lead / Product / Skill / Integration。请实际完成以下聚焦工作与验证，不要只给计划。仓库：https://github.com/suiyisuixing/concept-to-code-learning。本地先确认当前仓库根目录及 Git remote；若尚未克隆，通过私有仓库地址取得本人授权的 checkout，不能猜测或覆盖其他项目。使用本人 GitHub 账号，不共享凭据。若当前账号不是 @suiyisuixing，停止 GitHub 写操作，不复制或共享 Token。

指定分支：`feat/sprint-1-integration-contracts`。前置门禁全部满足后，从已更新 main 创建；已有同名分支先检查归属和状态，不能重置。主 Issue：[5](https://github.com/suiyisuixing/concept-to-code-learning/issues/5)。

## 本次目标与范围

在正式 v0.2 基线后创建此分支。本轮只审查六合同，落实 DocumentContext/GitHubCodeSource/GroundedExplanation/SavedNote 的最小兼容增量，定义 DocumentContextProvider、GitHubSourceVerifier、GroundedTutorProvider、NoteStore 接口与 VerticalSliceService，提供明确 Fixture Adapter、Provider 工厂、失败门禁和端到端测试壳。补 AGENTS、Sprint 文档、角色提示词、真实成员职责；CODEOWNERS 仅针对实际目录调整。#27 的 NoteStore 属于 Lead。

允许公共合同变更仅限本次用户明确列出的 Sprint 必需字段与兼容方案；仍要记录原因、旧/新示例和兼容性测试。当前旧 API/笔记不能退化。不得实现完整 PPTX 解析器、GitHub 客户端、真实 Tutor 或 DGX 部署，也不修改既有 PR #56。

## 输入合同

现有六 JSON Schema、旧 v0.2 Fixture/笔记、用户授权本次最小增量、三成员模块职责及接口需求。

## 输出合同

四合同（含 file_hash/visible_text、provider_mode/unsupported_claims、explanation_snapshot）与兼容读取；可信 Provider 接缝和服务端快照；默认全 Fixture，真实实现未接入时明确错误。只要有 Fixture，不能给真实 AI 完成状态。

## 验收标准

缺字段、伪 Verified、伪 VERIFIED_RUNNABLE、伪造来源、无显式保存均失败；保存后变更输入对象/源文件/来源不会改旧笔记，重启可读；任一 Provider 失败下游不继续，无模型配置不回退云；旧 76 个 Python/5 个前端基线与所有新测试实际通过。把新增数与旧基线分开记录，不预估成实际结果。

提交信息：`chore: prepare sprint 1 real learning vertical slice`。
PR 标题：`[Sprint 1] Freeze contracts and integration seams for the first real slice`。
本 PR 是 #5 合同准备；Document/GitHub/Tutor 合并后另开聚焦集成 PR 完成 #52，不能现在代做成员业务。后续重用本提示词先检查当前 PR 是否已完成，不重复创建标签、分支或 Issue。

## 共同工作规则

先读取仓库 AGENTS.md、docs/sprint-1-first-real-vertical-slice.md、docs/sprint-1-contract-review.md、当前 API/Schema/测试与对应 Issue。本角色负责在此 PR 提交合同，无需等待自己的 PR 先合并才能实现。若此分支/PR 已存在，审查并继续同一 PR，不重复创建；若已完成并等待审核，报告当前结果，后续最终集成须等三个模块 PR。

核对 gh 当前账号、origin、分支和工作树；不得覆盖他人的未提交改动。核验 main 包含已合并的历史基线 pre-rules-v0.2.0。PR #56 的既有审批只是历史事实，不要求队员重新批准。共同合同是否生效取决于 Lead 合并记录；普通评论、标签、CI 和正式 Review 必须分别报告。

始终维持私有与零新付费；不购买/试用服务，不提交模型、Key、Token、真实学校/企业资料、其他私有仓库或完整外部仓库。文档和来源仓库只读；最小引用并保留许可；不得编造仓库、Commit、路径、符号、行号或许可证。搜索结果不是 Verified。Fixture/Mock/固定文本必须可见标记。无自动云回退；任何实际联网必须在用户明确授权的具体来源/本地模型范围内。

禁止直接推 main，禁止强推、reset --hard、改写历史或移动已有正式标签。一个分支/PR 只处理一个聚焦问题。未经 Lead 批准不得擅自修改公共 Schema；有冲突先写清最小变更原因，不私建另一套不兼容合同。Lead 是唯一最终审核人和唯一 main 合并人；可在 required CI 成功、Codex 独立差异审计、人工自检且无 P0/P1 后自行合并自己的 PR，无需外部批准。成员不得合并任何 PR。不要替其他角色实现完整模块。不要自动启动其他成员的 Codex 任务。

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

先提交到指定个人分支，推送后创建指向 main 的聚焦 PR，关联主 Issue，正文写行为、接口/兼容边界、失败路径、测试数量/命令与真实/Fixture 区别。核验远程当前 head 的 phase0-checks 成功，再完成 Codex 只读差异审计，由 Lead 人工检查关键文件并阅读已有团队建议。Lead 自有 PR 无需外部批准；所有条件满足后可自行合并。仅在人工自检真实完成后记录 LEAD_SELF_REVIEW_PASSED。Codex 不代填人工检查，不绕过 CI。

最终用中文输出 DONE/PARTIAL/BLOCKED/FAILED/NOT_ATTEMPTED：实际修改、Commit、PR URL、当前 head CI、新增测试数、未完成能力及后续依赖；不能用“接口存在”替代真实能力完成。
