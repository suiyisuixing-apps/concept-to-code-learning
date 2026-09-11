# 功能与证据矩阵

所有“通过”均限定到下列实际观测。测试替身位于 tests/full_delivery/conftest.py，文件头和所有能力/结果明确标为 FIXTURE；没有注册进生产工厂。

| 能力 | Lead 实现/组合测试 | 当前实际产品 | 后续负责人与缺口 |
|---|---|---|---|
| 四格式文档、分页/章节/选区 | DTO、上传接缝、服务端块/Unicode code-point/hash、文档变更拒绝通过 | Document factory 未交付；原网页仅合成 Markdown | inogi #66：真实解析、资产、阅读与整个 UI |
| 指定仓库/公开搜索/本地来源 | 三 scope、必要词、授权、候选选择、注册表、撤销授权、版本/hash 检查通过 | Source factory 未交付 | zch #67：真实取回/发现/静态核验/许可/本地句柄 |
| 两阶段教学/四难度 | plan → search/verify → explain、文档和源引用、模式约束通过 | Tutor factory 未交付；网页人工固定 Fixture | fqf #68：真实教学逻辑、模型客户端和评测 |
| 追问与双仓库比较 | 会话上下文和源版本保留、两个不同仓库判断通过 | 新 UI 和真实 Tutor 待接入 | inogi + fqf + zch，Lead 最后组合 |
| 无代码/许可未知 | 可仅文档讲解；许可未知只返回元数据，不展示原码，不假冒代码引用 | 替身接口验证通过 | 实际网络/许可和语义判定待来源模块实测 |
| 取消/超时/翻页 | HTTP 取消、迟到结果拒绝、导航 CAS、无静默 Fixture/云回退通过 | 中央服务可用；实际 Provider 取消能力待交付 | 各 Provider 必须协作取消、限制外部调用 |
| 来源笔记 | 显式保存/幂等/并发、编辑修订、查找、导出、确认删除、重启恢复通过 | 新 notes API 与存储已实现；完整网页待接入 | inogi 完成整个笔记 UI |
| 原有数据兼容 | 旧 API/Schema 保留，Sprint1桥接和 raw connection 关闭回归通过 | 原 checkout/个人数据库保持不变 | 未做真实数据库迁移 |
| 配置/依赖/启动 | 固定工厂、每角色参数、28项Python版本快照；Mac一命令启动可见 | 缺模块如实 UNAVAILABLE；网页清楚 Fixture | 成员新增依赖到位后 Lead 再汇总 |
| 可安装 Skill | 三文件 ZIP、loopback-only/无代理/拒绝重定向、中文 stdout、实际 HTTP 流程通过 | 是实际 API 客户端；不能补齐缺失后端 | 宿主触发、真实模型收益另验 |
| 目标硬件 | 未使用新硬件/模型/容器 | 原生 Windows、DGX NOT_TESTED | fqf 部署包 + Lead 最终实机验收 |

## 九条用户故事

| # | 场景与实际用例 | 自动组合 | 真实外部/产品 |
|---|---|---|---|
| 1 | PDF概念 → 指定仓库 → 讲解 → 显式笔记 | PASS（格式与源/模型均为替身） | BLOCKED：#66/#67/#68 |
| 2 | PPTX概念 → 自动发现 → 追问 → 固定来源 | PASS（服务端元数据/版本） | BLOCKED：真实 PPTX、检索、模型及 UI 点击 |
| 3 | DOCX → 公开搜索或权限缺口 | PASS（未授权不搜索；不冒充讲解成功） | BLOCKED：真实 DOCX/外部服务 |
| 4 | Markdown → 本地 dirty → 解释/保存 | PASS（合成 dirty 元数据，无伪造 permalink） | BLOCKED：真实本地仓库 Provider |
| 5 | 两个不同仓库同概念比较 | PASS（两条独立替身回执） | BLOCKED：真实相关性与教学质量 |
| 6 | 无相关代码仍可文档解释 | PASS（NO_VERIFIED_CODE，零伪源码） | BLOCKED：真实 Tutor |
| 7 | 伪造选区/来源回执/间接指令 | PASS（材料不授予来源身份；字段/引用拒绝） | 模型抗间接指令效果 NOT_TESTED |
| 8 | 网络/模型错误、取消、切页竞态 | PASS（注入失败 + 实际HTTP取消 + 迟到结果不提交） | 真实服务失败行为 NOT_TESTED |
| 9 | 保存/编辑/导出/重启 | PASS（真实 SQLite/HTTP，合成学习内容） | 用户真实资料未用于测试；完整新 UI 待交付 |

九条对应 tests/full_delivery/test_stories.py 的九个 test_story 用例；test_boundaries.py 补充每个重要边界。来源真实性、AST结果、许可观察、语义相关性、推导/实际运行、模型使用量分别表达；任何一个绿勾不代表其他维度完成。
