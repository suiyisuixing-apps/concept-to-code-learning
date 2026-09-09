# 续接位置 · 完整模块交付后的集成

记录UTC：2026-09-09T08:04:56.171051+00:00。当前分支 `feat/full-learning-integration`；实现 Head `53dc7bb187307cd84cc2c9f92903e0e959986361`；main `369acd673d2ae0d1ae3bc8f591a2c7e51e4dc459`；PR #69：https://github.com/suiyisuixing/concept-to-code-learning/pull/69。最终报告提交后的Head从PR当前head与封存记录核对。

已完成的独立Lead实现和264+5本地回归见 IMPLEMENTATION/VALIDATION；不要重新设计合同或重新建仓库。测试、demo和截图均使用隔离合成资料；原有个人数据库不作试验。历史PR作者/提交保留，不reset、不force-push、不改旧tag。

## 下一项可执行动作

1. 取得#66/#67/#68的实际模块PR和精确Head。当前均未交付；不是把某人的编码/入队PR当成完整产品模块。读取其HANDOFF/依赖/测试/真实证据，正常合入新的隔离feature候选，保留作者。不要求先等对方进入main。
2. 对照 full_learning/ports.py 和 INTERFACES.md 接入三个固定factory，Lead只做最小适配和依赖汇总。apps/web全部由inogi负责；若需要破坏共同合同语义，明确给出兼容方案再由Lead决定。
3. 在候选临时数据目录重跑既有8项检查和九个故事；实际解析/真实来源/模型端点就绪后补live矩阵及Skill同模型对照。无端点不静默换云，无DGX不编硬件结果。

真实补证的最短路径：先一份用户授权真实文档、一处固定许可清楚的真实来源、一个已授权本机模型端点，通过实际UI导入/提问/保存后导出核对；再扩展四格式、三来源模式、四难度、追问/两库比较与失败路径。原生Windows完成中文目录/默认编码/句柄释放/启动；DGX按fqf部署包在获授权实机验证。没有这些条件时保留对应NOT_TESTED/BLOCKED，继续其他可测项。

## 已知失败/风险与再运行

- 完整npm audit退出1：同一Vitest开发依赖公告的2项moderate；生产依赖audit0。前端主版本调整交给#66提出理由并验证。
- 本地最终264项Python、5项前端、schema检查均通过；保留2项Python弃用警告。中间一次导入排序检查失败已修复；最初sandbox地址语法不支持、普通Git传输超时均不是产品测试通过，原日志保留本地。
- Git标准push超时后，仅用现有凭据的GitHub对象API发布同一Git SHA并做非强制fast-forward，验证原作者/parent/tree/commit身份；没有扩scope、amend或历史改写。
- 复制备份须正常停止软件后复制整个data目录。新learning-v1.sqlite3独立，不迁移旧笔记。回滚候选代码前保留新数据库与导出；旧代码不认识新notes，不代表新记录应删除。

复验命令：安装依赖、ruff、pytest、doctor/demo、npm ci/test/build见 VALIDATION.md。只在新代码、真实模块或失败证据改变后重跑相关检查；不定时空轮询或不断消耗CI。

用户最终决定前保持PR未合并，人工检查与LEAD_APPROVED不得由代理代填。
