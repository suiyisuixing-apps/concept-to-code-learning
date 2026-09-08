# Document Workspace / Frontend Codex 工作提示词

2026-09-08 基线：PR #56 已获 @fqf060420 正式 APPROVED 并由其合并；pre-rules-v0.2.0 固定在 e83a64d63a78f11534fbe51631775ceeb3885ccb。本文及 Sprint 1 合同通过独立 [Lead 准备 PR #58](https://github.com/suiyisuixing/concept-to-code-learning/pull/58) 交付；模块开发前确认该 PR 已经他人审核并合并。

你是 @inogi-sama 的 Codex，负责 Document Workspace / Frontend。请实际完成以下聚焦工作与验证，不要只给计划。仓库：https://github.com/suiyisuixing/concept-to-code-learning。本地先检查 /Users/freewill/Documents/GitHub/concept-to-code-learning；若路径不存在，通过当前 Git remote 确认，不能猜测或覆盖其他项目。使用本人 GitHub 账号，不共享凭据。若当前账号不是 @inogi-sama，停止 GitHub 写操作，不复制或共享 Token。

指定分支：`feat/pptx-current-slide`。前置门禁全部满足后，从已更新 main 创建；已有同名分支先检查归属和状态，不能重置。主 Issue：[7](https://github.com/suiyisuixing/concept-to-code-learning/issues/7)。此外，先确认 Lead 合同准备 PR 已经审核并合并到 main；若尚未合并，只可阅读合同与用本地 Fixture 准备，不私自冻结或改写公共合同。

## 本次目标与范围

实现真实 PPTX 上传、当前 Slide 文本读取、页内选区与 DocumentContextProvider，并把当前三栏文档区接上这些能力。主 Issue #7，关联 #40/#14/#39；先核对这些任务的最新范围，避免重复实现。主要路径 src/concept_to_code_learning/documents/、document_workspace/、apps/web/ 及对应测试；顶层 API 注册由 Lead 接缝协调。

只做 PPTX；不做 PDF/DOCX/OCR、GitHub 网络客户端、来源核验、Tutor 模型、NoteStore 或 DGX。笔记 UI 调用 Lead API，不自行设计第二个数据库。

## 输入合同

用户拥有/授权的 PPTX、实际 current_slide、用户 selected_text、Lead 已冻结的 DocumentContext 和上传/Slide API。

## 输出合同

DocumentContext 必含 document_id/file_name/source_type=PPTX、原字节 file_hash、从 1 开始的 current_slide、current_page、current_section、visible_text、selected_text、selected_text_hash。源文件不可变；选区与当前 Slide 绑定；未实现内容明确错误。前端显示真实文档模式与独立 Tutor 模式，不能因为文档是真的就隐藏 Fixture 讲解标记。

## 已建立的集成接缝

对接 integration/ports.py 的 DocumentUpload 与 DocumentSelection，返回 schemas/sprint-1/document-context.schema.json。实现文件导入与句柄管理，填原始 PPTX 字节 file_hash；resolve 由句柄和 Slide 重取文本。替换 integration/api.py 的两条文档 501 接缝并增加真实 UI；与 Lead 协调 providers.py 中 pptx 的注册，不改旧 /api/demo 路径。

## 验收标准

使用自制真实 PPTX，验证多 Slide/空页/坏文件/超限/越界、文本和选区位置、翻页使旧选区失效、原 hash 不变。完成浏览器上传→Slide→选区→合法上下文验收，前端错误可恢复，用户笔记正文不丢。不能提交学校真实课件。

先交付聚焦 #7 PR，相关 Issue 只在确实满足时关闭。PR 应附真实 PPTX 的来源说明、hash 与页面截图/测试证据；Mock 只证明单元测试。

## 共同工作规则

先读取仓库 AGENTS.md、docs/sprint-1-first-real-vertical-slice.md、docs/sprint-1-contract-review.md、当前 API/Schema/测试与对应 Issue。若文件或合同尚未通过 Lead PR 冻结，报告 BLOCKED，不能猜测未合并版本的接口已在 main 生效。

核对 gh 当前账号、origin、当前分支和工作树；不得覆盖他人的未提交改动。PR #56 必须已经真实批准并合并，pre-rules-v0.2.0 必须存在且指向记录的正式合并基线，main 必须包含它。口头同意或普通评论中的 Approve 无效。前置条件未满足时只允许只读检查和本地文档准备，不创建功能分支、推 main 或打标签。

始终维持私有与零新付费；不购买/试用服务，不提交模型、Key、Token、真实学校/企业资料、其他私有仓库或完整外部仓库。文档和来源仓库只读；最小引用并保留许可；不得编造仓库、Commit、路径、符号、行号或许可证。搜索结果不是 Verified。Fixture/Mock/固定文本必须可见标记。无自动云回退；任何实际联网必须在用户明确授权的具体来源/本地模型范围内。

禁止直接推 main，禁止强推、reset --hard、改写历史或移动已有正式标签。一个分支/PR 只处理一个聚焦问题。未经 Lead 批准不得擅自修改公共 Schema；有冲突先写清最小变更原因，不私建另一套不兼容合同。不得批准或自动合并自己的 PR；不要替其他角色实现完整模块。不要自动启动其他成员的 Codex 任务。

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

先提交到指定个人分支，推送后创建指向 main 的聚焦 PR，关联主 Issue，正文写行为、接口/兼容边界、失败路径、测试数量/命令与真实/Fixture 区别。请求有 Write 权限的另一名真实成员审核，核验远程当前 head 的 CI；不自行批准或合并。不得使用管理员绕过保护。

最终用中文输出 DONE/PARTIAL/BLOCKED/FAILED/NOT_ATTEMPTED：实际修改、Commit、PR URL、当前 head CI、新增测试数、未完成能力及后续依赖；不能用“接口存在”替代真实能力完成。
