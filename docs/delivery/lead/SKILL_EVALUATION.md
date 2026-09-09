# Skill 交付与对照记录

代码：`53dc7bb187307cd84cc2c9f92903e0e959986361`。入口为根 SKILL.md + scripts/learning_client.py + references/full-learning-api.md。执行 `python scripts/package_skill.py` 生成 dist/skills/concept-to-code-learning.zip；目标宿主需要 Python3.12 和可连接的本机后台。无需开发者本机路径，不自动安装后台/模型或假设宿主一定触发。

| 验证 | 结果 | 实际含义 |
|---|---|---|
| Skill 格式校验 | PASS | quick_validate.py 返回 Skill is valid |
| 三文件 ZIP 解包、实际脚本 | PASS | 解到独立临时目录执行；中文/emoji在 GBK stdout 环境输出UTF-8 |
| 导入→上下文→讲解→独立保存→导出→确认删除 | PASS / FIXTURE | 真 loopback HTTP + 真 SQLite，Document/Source/Tutor 为测试替身 |
| 有包装客户端 / 无包装直接 HTTP | PASS / TRANSPORT_PARITY_ONLY | 同一冻结上下文/问题/难度/源范围、相同替身；回答段、来源版本/hash一致，均无自动笔记 |
| 有 Skill / 无 Skill 的真实模型教学收益 | NOT_TESTED | 没有完整 Tutor/真实端点，未产生质量分数、Token改善或提效百分比 |
| 宿主自动触发/比赛资格 | NOT_TESTED | 没有依据 ZIP 或接口测试做推断 |

复验受控对照：`pytest -q tests/full_delivery/test_contracts_and_skill.py -k portable_skill`。用例中比较有包装客户端与直接HTTP入口，不能把它称为有/无宿主Skill的真实模型评测。

## 真实对照的固定协议

收到三模块精确Head和已经授权的模型端点后，使用下表记录，而不是以测试数代替效果。建议先做9个故事中可真实完成的案例，报告实际分母，不凑数量。A/B顺序交替，每个案例使用独立会话和空笔记库。

- 两组固定同一模型ID、权重/量化版本、推理参数、上下文限制、工具列表、工具权限、最大工具次数和Token预算；同一文档字节/hash/选区/问题、同一仓库固定Commit与许可记录。
- A组宿主显式加载本Skill；B组使用相同工具能力但不加载Skill文本。不能删除B组取源码工具来人为抬高差异。记录宿主名/版本、实际加载证据和每次调用轨迹。
- 真实任务至少包含一条真实文档+真实来源+真实模型。原文引用、版本/行/许可、笔记内容完整性可以确定性核对；教学正确性/相关性由Lead逐条看答案判定，AST存在不算教学正确。
- 记录成功/失败/无来源/权限缺口、答非所问、虚构引用、用户文字保留、取消行为、实际时延。Token仅用provider usage；缺失标NOT_OBSERVED，估算单列。
- 不执行第三方代码，不导入用户未授权私有资料，不为评测扩张来源/模型网络范围。先看失败日志和实际答案，再判断是否有收益。

每组记录字段：case_id、condition(with_skill/without_skill)、repo_head、host/version、model_id/weight_revision、parameters、document_sha256/locator、question、source_commit/hash、scope、tool_budget、token_budget、actual_tool_calls、usage_source、latency_ms、answer_artifact、note_artifact、source_truth_result、teaching_result、judge、limitations。当前这些真实字段留空，不伪造分数。
