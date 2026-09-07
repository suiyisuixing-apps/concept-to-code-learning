> 以下记录保留 Phase 0 历史，不代表当前范围或本轮实时状态。当前决策见 rescope-decision.md。

# 既有资产候选登记

读取时间：2026-09-07。内容检查固定于本地 HEAD，通过 GitHub API 另行读取远程 HEAD。
本地与远程不一致时分别记录，不拉取、不合并、不改动现有仓库；未提交改动不归入检查基线。

| 仓库 | 本轮内容读取 Commit SHA | 当前远程 HEAD | 来源许可 | 状态 |
| --- | --- | --- | --- | --- |
| suiyisuixing/ai-workbench | `01b83f8a5f14d4ae721cf8da982055024ff67dd7` | `49fac9e0d8a7e0435e33d7167fd27a1d82af96b8` | LICENSE.txt 明确尚未选择开源许可 | CANDIDATE_NOT_IMPORTED |
| suiyisuixing/classnote-ai | `d296de0c0a64547edd6a276f8a2e770d4cc1583c` | `d296de0c0a64547edd6a276f8a2e770d4cc1583c` | 本地 HEAD 的 LICENSE 为 MIT | CANDIDATE_NOT_IMPORTED |
| suiyisuixing/llm-security-lab | `2ee13d864e609787537f4f716a34f0b50498cb3b` | `e6597cbaf0488bdc50421d5b97ed34830228cd1b` | 本地 HEAD 的 LICENSE 为 MIT | CANDIDATE_NOT_IMPORTED |

| 仓库 | 可借鉴能力 | 实际检查的候选文件/模块 | 计划 |
| --- | --- | --- | --- |
| AI Workbench | 知识与源码关联、Git Worktree 隔离、任务/证据、可验证状态、发布门禁 | backend/app/project_knowledge/symbols.py; backend/app/services/worktrees.py; backend/app/organization/evidence.py; scripts/run_release_gate.py | 仅参考设计；若后续重写另建 PR；当前不复制 |
| ClassNote AI | PPTX/DOCX/PDF 本地处理、来源定位、原文件不可变、本地隐私边界 | application/document_service.py; application/document_renderers.py; PRIVACY.md | 仅参考架构；当前不复制；不能把 GUI 文档渲染当作已完成概念提取 |
| LLM Security Lab | Python/FastAPI、真实测试、权限/检索/审计概念、入职 Demo 候选 | backend/app/main.py; backend/app/audit.py; tests/test_auth_jwt.py | 后续 #22 固定可获取 commit，以说明或 setup 获取到忽略目录；不整体复制进 Git 历史 |

本轮没有导入任何实现代码，也没有运行这些仓库的测试或声称验证其完整运行质量。
AI Workbench 存在四份已暂存报告；LLM Security Lab 存在 live_evaluation.py 修改和未跟踪的
live_oracles.py；均保留。许可记录只描述实际读取的文件，不替代后续复用及比赛规则审查。

## Phase 0.5 实际复用

新增公开 fastapi/fastapi 在固定 Commit 50113da16fec53b66b80d75e80a89296de4fa5a5 的 12–14 行最小引用与 MIT 许可通知，见 demo/learning/README.md。未复制完整仓库，未改动原有 ai-workbench/classnote-ai/llm-security-lab 仓库。没有使用 LLM Security Lab 作为唯一演示来源。
