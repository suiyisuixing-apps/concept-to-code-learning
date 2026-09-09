# Lead 交付 · PARTIAL

分支：`feat/full-learning-integration`。基线：`BASELINE_KIND=UNMERGED_CONTRACT`，main `369acd673d2ae0d1ae3bc8f591a2c7e51e4dc459`；实现 Head `53dc7bb187307cd84cc2c9f92903e0e959986361`；[PR #69](https://github.com/suiyisuixing/concept-to-code-learning/pull/69)。后续报告/截图提交不改变运行代码；最终发布 Head 与其 CI 在PR正文及交付封存记录中给出，不能把实现Head的CI冒充后续Head。

代码已准备：新的兼容合同、中央服务与API、三Provider接缝、服务端上下文与来源边界、事务来源笔记、Skill、单命令启动。三位成员各有一份完整任务书和主Issue，可持续完成整个模块；没有冒名执行其成员会话或私信。

- Lead：#65；docs/codex-prompts/full-delivery/01_LEAD_FULL_EXECUTION.md（用户提供原文）。
- inogi-sama：#66；02_INOGI_FULL_EXECUTION.md（Lead整理稿，整个React界面与四格式文档）。
- zchzbjklg：#67；03_ZCHZBJKLG_FULL_EXECUTION.md（Lead整理稿，来源发现/核验/本地仓库）。
- fqf060420：#68；04_FQF060420_FULL_EXECUTION.md（Lead整理稿，Tutor/模型/评测/DGX）。

02–04的原附件没有随本轮提供；整理稿依据用户给出的完整角色范围及共同A/B协议编写，均含完整公共约定并标明来源，不冒充未提供的原文。

启动、模型/网络/系统配置、停止与备份见 ../../full-delivery/RUNNING.md；接口见 ../../full-delivery/INTERFACES.md 和openapi.json。准备一次依赖与前端构建后，在repo根目录运行 `python scripts/start.py`；已有本机venv可用 `.venv/bin/python scripts/start.py`。

## 五分钟审核

1. 打开网页与 `/api/learning/v1/capabilities`：网页应标Fixture；三真实模块未交付应UNAVAILABLE，notes与legacy可用。看 evidence/ui-final.png。
2. 看 full_learning/service.py 的 context重读、search/verify/输出引用、取消完成检查；看 store.py 的事务幂等/修订快照。不要求先去找文件名/行号才能问概念。
3. 看 FUNCTION_MATRIX.md 和 VALIDATION.md，确认九条自动化故事都是替身组合；SQLite/HTTP真实执行不等于模型真实执行。看 SKILL_EVALUATION.md 的对照边界。
4. 看 PR #69 的最新Head、required CI与依赖PR表；保留原作者历史，#64已合并，#58/#60/#62/#59仍按现场状态判断。
5. 用户亲自看关键文件/界面再决定。当前不存在完整真实学习链，不能把此候选批准为全产品完成；人工审核框保持未勾选。

继续所需：见 CONTINUATION.md。当前所有可独立执行的Lead工作已完成，尚未完成项明确归属成员交付、真实外部条件与最终人工验收；没有自动合并、后台运行或后续通知承诺。
