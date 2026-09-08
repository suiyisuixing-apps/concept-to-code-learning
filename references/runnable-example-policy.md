# 可选运行验证

运行不属于强制学习/考核流程。执行前确认用户授权、命令、来源许可、依赖与隔离边界。用可丢弃工作目录，限制资源与时间，不携带生产凭证，默认禁用网络，不修改原始仓库。

原样来源、改编示例和 AI 新代码分别标注。实际成功运行后记录命令、退出码 0、stdout/stderr、执行时间和隔离说明，才可 VERIFIED_RUNNABLE。未运行是 NOT_RUN，失败或证据不足是 NEEDS_CONFIRMATION/REJECTED。仅通过静态 AST 或测试别的文件不能证明当前片段可运行。

当前新 FastAPI 引用为 NOT_RUN。Phase 0 demo 的合成 active-user 示例仍运行并记录独立回归证据，不能借此标记 GitHub 片段运行成功。
