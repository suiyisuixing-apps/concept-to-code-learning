# 公共数据接口 V0.1

四个独立 JSON Schema 使用 Draft 2020-12，无远程引用；禁止多余属性。必填字段可通过
`contracts.validate_record` 校验，`doctor` 同时检查 Schema 自身是否合法。

| Schema | 必填信息 | 有限状态 |
| --- | --- | --- |
| concept | ID、名称、定义、目标、来源、置信度、未决问题 | extraction_status: FIXTURE_DEFINED / EXTRACTED / NEEDS_CONFIRMATION / UNSUPPORTED_INPUT |
| code-mapping | 概念 ID、commit、代码位置、测试、原因、核验状态、证据 | verification_status: VERIFIED / NEEDS_CONFIRMATION / REJECTED |
| learning-artifact | 概念 ID、讲解/示例/练习/评分器路径、状态、证据 | status: SCAFFOLD_DEMO / DRAFT / VERIFIED_RUNNABLE / GRADED_PASS / GRADED_FAIL / NEEDS_CONFIRMATION |
| drift-finding | finding ID、概念 ID、文档断言、代码观察、双方来源、责任角色、解决记录 | status: NEEDS_CONFIRMATION / CONFIRMED_DRIFT / NO_DRIFT / RESOLVED |

来源类型：PPTX 要求 slide；DOCX 要求 section 与 paragraph；PDF 要求 page；
MARKDOWN_FIXTURE 要求 section 与 paragraph。位置从 1 开始，quote_hash 为被引段落
原始 UTF-8 字节的 SHA-256，非整个文件的哈希。每个来源保留全部定位字段，无意义处为 null。

代码类型：function / async_function / class / route / configuration / test。AST 负责
Python 符号和行号，文件系统负责路径存在；配置不能仅因文件存在而冒充 AST 核验。
`repository_commit` 在首次提交前允许 null；此时 evidence 必须指出 UNCOMMITTED_FIXTURE。
提交后记录真实 HEAD，同时保存文件哈希与 dirty 标识，不能把工作区变化当成 commit 内容。

缺失的练习和评分器路径必须是 null，不可编造。`VERIFIED_RUNNABLE` 至少要求真实示例
路径与执行证据；`GRADED_PASS/FAIL` 还必须给出练习、评分器路径和确定性结果。
Phase 0 的 artifact 状态始终是 SCAFFOLD_DEMO，即使其中的固定示例确实运行成功。

报告外层固定 `mode: FIXTURE`、`status: SCAFFOLD_DEMO`；它们不等同于每个结构内部
的领域状态。存在性核验不代表语义映射自动成立，pytest 通过不代表教学有效。
新增或改变接口需 Lead 审核，并提供生产者与消费者样例、负例和迁移说明。
