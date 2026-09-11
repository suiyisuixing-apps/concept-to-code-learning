# Skill 真实同条件检查

2026-09-11 在完整候选上，使用同一本地 Qwen 模型、同一 Markdown 上下文、问题、Engineering 级别、授权范围、token 上限及同一份服务端冻结来源，比较直接 HTTP 与 scripts/learning_client.py explain。

两侧都返回 GROUNDED；文档快照、CodeEvidence、provider_info 相同，均报告 973 输入/645 输出 tokens；模型阶段分别约 14.529/14.732 秒。没有因 Skill 自动保存笔记。这验证实际模型条件下的传输和证据一致性。

它不测宿主自动触发或教学收益。没有无根据的正确率、学习进步或赛事资格声明。保留原先离线 fake-service smoke 的独立分类。完整结果摘要见 product-completion/VERIFICATION.json；原始运行文件保存在本次本地证据目录，不含真实用户材料。
