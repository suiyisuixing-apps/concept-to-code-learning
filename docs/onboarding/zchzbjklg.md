# @zchzbjklg 入队记录

关联 [Issue #54](https://github.com/suiyisuixing/concept-to-code-learning/issues/54) 与 [PR #59](https://github.com/suiyisuixing/concept-to-code-learning/pull/59)。原记录日期 2026-09-08，Lead 于 2026-09-09 整理格式和证据范围。本 PR 只记录入队环境与检查，不是产品功能。

## 成员原始自报

原提交 `2f5cca7f4a03e29e26334a85ff7fe892d8122434` 未附完整终端日志和逐条退出码。下面保留自报，不将其标成独立复核结果。

| 项目 | 成员记录 | 证据边界 |
| --- | --- | --- |
| 系统 | Windows 11 + Git Bash | 成员自报 |
| Python | 3.12.10 | 成员自报，处于项目要求 >=3.12,<3.13 |
| Node | 24.20.0 | 成员自报；CI 工作流使用 Node 20 |
| Python 检查 | ruff、pytest 74 passed、doctor DONE | 未给完整失败/错误统计或退出码，不能判定完整套件全绿 |
| 前端 | npm ci、test 5 passed、build | 成员自报，未给完整日志 |
| demo | 原文件未记录 | 尚无该次 Windows demo 证据 |
| 2FA | 已开启 | 个人安全设置自报，不索取安全码 |

## Lead 本轮可复核检查

以下记录 Codex 在独立临时目录内执行的 macOS 检查；与上面的 Windows 自报分开。测试使用临时 C2C_DATA_DIR，不改已有个人笔记。

<!-- lead-check-results -->
执行日期：2026-09-09。平台：macOS；Python 3.12.14；Node v26.6.0。检出基线 `e83a64d63a78f11534fbe51631775ceeb3885ccb` 加本 PR 文档改动；这些是 Lead/Codex 本机证据，不是成员 Windows 复测。

| 实际命令 | 退出码 | 实际结果 |
| --- | --- | --- |
| `python -m pip install -e ".[dev]"` | 0 | 安装成功 |
| `ruff check .` | 0 | 通过 |
| `pytest -q` | 0 | 76 passed；依赖弃用警告 2 条 |
| `python scripts/tutor.py doctor` | 0 | DONE |
| `python scripts/tutor.py demo` | 0 | FIXTURE / SCAFFOLD_DEMO 成功 |
| `npm --prefix apps/web ci` | 0 | 依赖安装成功 |
| `npm --prefix apps/web test` | 0 | 5 passed |
| `npm --prefix apps/web run build` | 0 | 构建成功 |
<!-- /lead-check-results -->

远程 CI 由 PR 当前 Head 的 phase0-checks 提供；旧 Head 的成功不能代替新 Head 检查。原始 PR 的 [CI 34234441819](https://github.com/suiyisuixing/concept-to-code-learning/actions/runs/34234441819) 属于历史版本。

## 当前协作规则与待完成项

由 @suiyisuixing 唯一最终审核并合并；成员不得合并自己或他人的 PR，所有 PR 必须通过 phase0-checks。队员可向 Lead 提出非阻塞 Comment 建议，不需要互相强制 Approve。治理决策见 Issue #63 / PR #64；不得把未合并文档视为已进入 main。

当前尚缺该成员在最新集成版本上的完整 Windows 命令、退出码、通过/失败/错误统计，尤其是 demo。#60 和 #62 分别处理 UTF-8 和 SQLite；本入队文档不代替这些功能修复或 Windows 验收。Issue #54 的完成状态仍由真实证据和 Lead 决定，不因整理文档自动关闭。
