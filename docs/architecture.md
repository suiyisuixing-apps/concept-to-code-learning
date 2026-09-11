> 2026-09-09 当前执行范围： [完整学习版](full-delivery/PLAN.md)；[新接口与职责](full-delivery/INTERFACES.md)。以下旧阶段说明保留作兼容和历史参考。

# 架构与接缝

```text
apps/web (React + Vite)
  文档页/选区 → /api/learning/explain → 讲解 + document_citations + github_sources
                  ↓ 用户明确保存
              /api/notes → SQLite 追加记录 → 刷新/重启后读取
FastAPI api.py → tutor/fixture.py → 六个本地 JSON Schema
             → store.py（服务端来源快照，不接受客户端替换来源）
```

`documents/` 与 `document_workspace/` 是真实文件导入、定位和不可变性接缝；`github_intelligence/` 与 `code_intel/` 是三种来源模式和通用核验接缝；`tutor/` 与 `runtime/` 是概念、讲解级别和本地模型接缝；`execution/` 负责未来隔离验证；`evals/` 负责 Grounding 对照。

上述空模块均为扩展边界，不是已实现功能。当前 FixtureTutor 不访问网络，只读取合成文档与一条冻结引用；四种文本为人工固定内容，不是模型输出。`scaffold.py` 与 `legacy_contracts.py` 保留 Phase 0 回归链，旧 grading/drift 字段不会进入新 UI。

本地服务只绑定 127.0.0.1，Host allowlist 限定本地；没有开放 CORS、鉴权、多人服务器部署、遥测或同步。该骨架不应直接部署到公网。个人笔记只增不改；解释缓存与笔记持久化位于当前项目的本地数据库。前端的笔记正文与讲解状态独立，再提问不会清空用户文字。
