# GitHub 来源策略

A 用户指定仓库：保留 owner/name allowlist；B 本地仓库：只读、授权根目录、记录 Git 状态；C 公开搜索：明确授权、记录 query、只搜索公开仓库。所有候选先 UNVERIFIED，不凭搜索摘要作证。

核验顺序：仓库存在与 visibility → immutable commit → 固定版本文件 → AST/相应解析器符号 → 原文行区间与 hash → 同 Commit 许可证 → 与知识点相关性。任一缺证据时 NEEDS_CONFIRMATION；来源状态与运行状态分开。一次手工冻结核验不是通用引擎。

只引用必要片段，保留许可；不复制全仓库，不改来源，不外传私有内容。AI_GENERATED、ADAPTED_FROM_SOURCE、原始已核验代码分开。多仓库比较必须逐条核验与引用。当前 search/verify HTTP 501，无外网请求。
