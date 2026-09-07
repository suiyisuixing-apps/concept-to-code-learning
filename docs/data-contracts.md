# 六个活动契约

六个根目录 JSON Schema 使用 Draft 2020-12、required、additionalProperties=false 和有限状态。验证器禁止外部 $ref，不会触发远程加载。

| Schema | 主要内容 | 消费者 |
| --- | --- | --- |
| document-context | document ID、文件、格式、page/slide/section、选区及 hash | 前端/文档/讲解 |
| learning-concept | 概念 ID、名字、描述、关键词、文档上下文、状态 | Tutor |
| github-code-source | owner/name/URL/visibility、SHA、branch/tag、文件、符号、行号、片段/hash、许可证/URL、时间、核验、相关性 | 来源卡/Tutor/笔记 |
| grounded-explanation | 问题、上下文、概念、级别、讲解、文档引用、GitHub 来源、比较、运行状态、待核验项 | Tutor/UI |
| saved-note | 用户标题和正文、解释 ID、双来源、时间、authored_by_user、解释快照 | 本地持久化 |
| runnable-example | 来源类型、source IDs、运行状态、命令、退出码、输出、执行时间、隔离描述 | 可选执行 |

`repository` 语义由 owner/name/URL/visibility 四字段表达；`lines` 为 line_start/end；`license` 为 license_name/url；`source_status` 是显式字段。GitHub 核验状态与示例执行状态独立，不能互相推导。

有限状态：GITHUB_SOURCE_VERIFIED、GITHUB_SOURCE_UNVERIFIED、LOCAL_REPOSITORY_VERIFIED、ADAPTED_FROM_SOURCE、AI_GENERATED、VERIFIED_RUNNABLE、NOT_RUN、NEEDS_CONFIRMATION、REJECTED。每个字段只接受对应子集。Fixture 外层 mode/status 不等于来源/执行结论。

已核验 GitHub 引用必须具备完整 SHA、路径、符号、行号、许可与核验方法；运行 VERIFIED_RUNNABLE 必须携带成功退出码、命令、时间和隔离。哈希一致性、行区间顺序、上下文归属由运行时验证补充 JSON Schema。固定讲解中的 concept.status=NEEDS_CONFIRMATION 表示自动概念识别尚未实现；UI 明确这是人工 Fixture，不代表发生了 AI 推理。

`schemas/legacy/` 保存 4 个 Phase 0 契约，供旧回归用例验证，不是新软件公共接口。不复用旧 VERIFIED、GRADED_PASS 或员工掌握声明。
