# Issue 登记册（Phase 0.5）

36 个旧 Issues 全部保留，新增 16 个核心任务和 3 个入队任务，共 55 个。关闭旧考核 #25/#26/#33 前保留指定评论；#21/#34 为 post-MVP/P2，无 M4 依赖。新任务的前置关系已检查无环。所有本轮代码相关任务在 PR 审核合并前保持开放。

| Issue | 标题 | 主责 | 状态 | Milestone |
| --- | --- | --- | --- | --- |
| [#1](https://github.com/suiyisuixing/concept-to-code-learning/issues/1) | Freeze MVP scope and non-goals | @suiyisuixing | closed | M0 – Foundation and Contracts |
| [#2](https://github.com/suiyisuixing/concept-to-code-learning/issues/2) | Draft SKILL.md V0.1 | @suiyisuixing | closed | M0 – Foundation and Contracts |
| [#3](https://github.com/suiyisuixing/concept-to-code-learning/issues/3) | Define shared JSON contracts | @suiyisuixing | closed | M0 – Foundation and Contracts |
| [#4](https://github.com/suiyisuixing/concept-to-code-learning/issues/4) | Implement tutor CLI scaffold | @suiyisuixing | closed | M0 – Foundation and Contracts |
| [#5](https://github.com/suiyisuixing/concept-to-code-learning/issues/5) | Integrate document, code and learning pipelines | @suiyisuixing | open | M4 – Pre-Rules Demo Freeze |
| [#6](https://github.com/suiyisuixing/concept-to-code-learning/issues/6) | Maintain competition provenance and reuse ledger | @suiyisuixing | open | M4 – Pre-Rules Demo Freeze |
| [#7](https://github.com/suiyisuixing/concept-to-code-learning/issues/7) | Implement PPTX parser with slide citations | @inogi-sama | open | M1 – Document Learning Workspace |
| [#8](https://github.com/suiyisuixing/concept-to-code-learning/issues/8) | Implement DOCX parser with section citations | @inogi-sama | open | M1 – Document Learning Workspace |
| [#9](https://github.com/suiyisuixing/concept-to-code-learning/issues/9) | Implement PDF parser with page citations | @inogi-sama | open | M1 – Document Learning Workspace |
| [#10](https://github.com/suiyisuixing/concept-to-code-learning/issues/10) | Build concept extraction pipeline | @fqf060420 | open | M1 – Document Learning Workspace |
| [#11](https://github.com/suiyisuixing/concept-to-code-learning/issues/11) | Preserve source provenance and merge duplicate concepts | @fqf060420 | open | M1 – Document Learning Workspace |
| [#12](https://github.com/suiyisuixing/concept-to-code-learning/issues/12) | Add local OpenAI-compatible model adapter | @fqf060420 | open | M5 – Competition Submission |
| [#13](https://github.com/suiyisuixing/concept-to-code-learning/issues/13) | Prepare DGX Spark runtime and deployment guide | @fqf060420 | open | M5 – Competition Submission |
| [#14](https://github.com/suiyisuixing/concept-to-code-learning/issues/14) | Build document extraction evaluation cases | @inogi-sama | open | M1 – Document Learning Workspace |
| [#15](https://github.com/suiyisuixing/concept-to-code-learning/issues/15) | Build Python repository and AST index | @zchzbjklg | open | M2 – GitHub Grounding and Verification |
| [#16](https://github.com/suiyisuixing/concept-to-code-learning/issues/16) | Index functions, classes, FastAPI routes, configuration and tests | @zchzbjklg | open | M2 – GitHub Grounding and Verification |
| [#17](https://github.com/suiyisuixing/concept-to-code-learning/issues/17) | Generate concept-to-code candidates | @zchzbjklg | open | M2 – GitHub Grounding and Verification |
| [#18](https://github.com/suiyisuixing/concept-to-code-learning/issues/18) | Verify files, symbols and line locations | @zchzbjklg | open | M2 – GitHub Grounding and Verification |
| [#19](https://github.com/suiyisuixing/concept-to-code-learning/issues/19) | Map concepts to relevant tests and commands | @zchzbjklg | open | M2 – GitHub Grounding and Verification |
| [#20](https://github.com/suiyisuixing/concept-to-code-learning/issues/20) | Implement isolated runnable-example executor | @zchzbjklg | open | M3 – Grounded Tutor Learning Loop |
| [#21](https://github.com/suiyisuixing/concept-to-code-learning/issues/21) | Implement documentation-to-code drift detector | @zchzbjklg | open | post-MVP |
| [#22](https://github.com/suiyisuixing/concept-to-code-learning/issues/22) | Pin licensed public GitHub demo code sources | @zchzbjklg | open | M4 – Pre-Rules Demo Freeze |
| [#23](https://github.com/suiyisuixing/concept-to-code-learning/issues/23) | Build document-centered grounded lesson generator | @fqf060420 | open | M3 – Grounded Tutor Learning Loop |
| [#24](https://github.com/suiyisuixing/concept-to-code-learning/issues/24) | Package optional source-backed runnable examples | @fqf060420 | open | M3 – Grounded Tutor Learning Loop |
| [#25](https://github.com/suiyisuixing/concept-to-code-learning/issues/25) | Create bounded project exercise templates | @fqf060420 | closed | M3 – Grounded Tutor Learning Loop |
| [#26](https://github.com/suiyisuixing/concept-to-code-learning/issues/26) | Implement deterministic exercise graders | @fqf060420 | closed | M3 – Grounded Tutor Learning Loop |
| [#27](https://github.com/suiyisuixing/concept-to-code-learning/issues/27) | Save source-backed personal learning notes | @fqf060420 | open | M3 – Grounded Tutor Learning Loop |
| [#28](https://github.com/suiyisuixing/concept-to-code-learning/issues/28) | Build Skill vs generic-chat baseline evaluation | @fqf060420 | open | M4 – Pre-Rules Demo Freeze |
| [#29](https://github.com/suiyisuixing/concept-to-code-learning/issues/29) | Build three-pane software UI and demo shell | @inogi-sama | open | M4 – Pre-Rules Demo Freeze |
| [#30](https://github.com/suiyisuixing/concept-to-code-learning/issues/30) | Prepare competition demo script and recording checklist | @fqf060420 | open | M5 – Competition Submission |
| [#31](https://github.com/suiyisuixing/concept-to-code-learning/issues/31) | Complete document-to-code learning vertical slice | @suiyisuixing | open | M2 – GitHub Grounding and Verification |
| [#32](https://github.com/suiyisuixing/concept-to-code-learning/issues/32) | Complete first runnable example | @zchzbjklg | open | M3 – Grounded Tutor Learning Loop |
| [#33](https://github.com/suiyisuixing/concept-to-code-learning/issues/33) | Complete first graded repository exercise | @fqf060420 | closed | M3 – Grounded Tutor Learning Loop |
| [#34](https://github.com/suiyisuixing/concept-to-code-learning/issues/34) | Demonstrate one documentation-code drift case | @zchzbjklg | open | post-MVP |
| [#35](https://github.com/suiyisuixing/concept-to-code-learning/issues/35) | Freeze pre-rules prototype | @suiyisuixing | open | M4 – Pre-Rules Demo Freeze |
| [#36](https://github.com/suiyisuixing/concept-to-code-learning/issues/36) | Run final learning-workspace competition acceptance suite | @suiyisuixing | open | M5 – Competition Submission |
| [#37](https://github.com/suiyisuixing/concept-to-code-learning/issues/37) | Rescope product as Concept-to-Code Learning | @suiyisuixing | open | M0.5 – Product Rescope and Team Onboarding |
| [#38](https://github.com/suiyisuixing/concept-to-code-learning/issues/38) | Rename repository and update package identity | @suiyisuixing | open | M0.5 – Product Rescope and Team Onboarding |
| [#39](https://github.com/suiyisuixing/concept-to-code-learning/issues/39) | Build three-pane learning workspace UI | @inogi-sama | open | M1 – Document Learning Workspace |
| [#40](https://github.com/suiyisuixing/concept-to-code-learning/issues/40) | Implement current-page and selected-text context | @inogi-sama | open | M1 – Document Learning Workspace |
| [#41](https://github.com/suiyisuixing/concept-to-code-learning/issues/41) | Implement source-backed note saving UI | @inogi-sama | open | M1 – Document Learning Workspace |
| [#42](https://github.com/suiyisuixing/concept-to-code-learning/issues/42) | Add frontend tests and build to CI | @inogi-sama | open | M0.5 – Product Rescope and Team Onboarding |
| [#43](https://github.com/suiyisuixing/concept-to-code-learning/issues/43) | Implement user-selected GitHub repository mode | @zchzbjklg | open | M2 – GitHub Grounding and Verification |
| [#44](https://github.com/suiyisuixing/concept-to-code-learning/issues/44) | Implement authorized local repository mode | @zchzbjklg | open | M2 – GitHub Grounding and Verification |
| [#45](https://github.com/suiyisuixing/concept-to-code-learning/issues/45) | Implement authorized public GitHub search mode | @zchzbjklg | open | M2 – GitHub Grounding and Verification |
| [#46](https://github.com/suiyisuixing/concept-to-code-learning/issues/46) | Verify repository, commit, file, symbol, lines and license | @zchzbjklg | open | M2 – GitHub Grounding and Verification |
| [#47](https://github.com/suiyisuixing/concept-to-code-learning/issues/47) | Build GitHub code evidence cards | @zchzbjklg | open | M2 – GitHub Grounding and Verification |
| [#48](https://github.com/suiyisuixing/concept-to-code-learning/issues/48) | Implement multi-repository comparison | @zchzbjklg | open | M2 – GitHub Grounding and Verification |
| [#49](https://github.com/suiyisuixing/concept-to-code-learning/issues/49) | Implement grounded explanation pipeline | @fqf060420 | open | M3 – Grounded Tutor Learning Loop |
| [#50](https://github.com/suiyisuixing/concept-to-code-learning/issues/50) | Implement explanation-level profiles | @fqf060420 | open | M3 – Grounded Tutor Learning Loop |
| [#51](https://github.com/suiyisuixing/concept-to-code-learning/issues/51) | Build generic-chat vs grounded-skill evaluation | @fqf060420 | open | M3 – Grounded Tutor Learning Loop |
| [#52](https://github.com/suiyisuixing/concept-to-code-learning/issues/52) | Build document-to-GitHub vertical slice | @suiyisuixing | open | M0.5 – Product Rescope and Team Onboarding |
| [#53](https://github.com/suiyisuixing/concept-to-code-learning/issues/53) | Team onboarding – @inogi-sama | @inogi-sama | open | M0.5 – Product Rescope and Team Onboarding |
| [#54](https://github.com/suiyisuixing/concept-to-code-learning/issues/54) | Team onboarding – @zchzbjklg | @zchzbjklg | open | M0.5 – Product Rescope and Team Onboarding |
| [#55](https://github.com/suiyisuixing/concept-to-code-learning/issues/55) | Team onboarding – @fqf060420 | @fqf060420 | open | M0.5 – Product Rescope and Team Onboarding |

## 2026-09-09 治理变更说明

上文保留当时的历史范围与状态，不作为当前审批门禁。此日起只有 @suiyisuixing 最终审核与合并 main；成员 PR 由 Lead 审核，Lead 自有 PR 经人工自检、Codex 审计和 required CI 后可自行合并，无需外部批准。PR/CI、禁止直接 Push/Force Push/删除 main 仍保留。参见 [治理政策](governance/lead-controlled-merge-policy.md)。Project 是否已创建仍需单独核验，治理迁移不证明 Project 完成。
