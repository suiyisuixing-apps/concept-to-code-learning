# 五分钟检查 — github_intelligence（Lead 复验用）

**分支**: `feat/67-source-failure-matrix`
**模块**: `src/concept_to_code_learning/github_intelligence/`
**本切片**: 仅新增测试与交付文档，**未改生产代码**（所以复验重点是"测试是否真的通过"与"是否真的没改代码"）

---

## 0. 前置：用项目 venv，不要用沙箱 python

本机 `python` 会解析到 workbuddy 沙箱的 **3.13**，而项目要求 `>=3.12,<3.13`。一律显式用 `.venv`：

```bash
cd ~/Desktop/concept-to-code-learning
export PYTHONUTF8=1
P=./.venv/Scripts/python.exe
$P --version          # 必须是 Python 3.12.10
```

---

## 1. 证明"确实没动生产代码"（10 秒）

```bash
git diff --stat origin/feat/full-learning-integration...HEAD
```

**预期**：`src/` 下 **零** 变更；只有 `tests/github_intelligence/test_source_failure_matrix.py` 与 `docs/delivery/zchzbjklg/*`。

再确认没碰公共契约与 CI：

```bash
git diff --name-only origin/feat/full-learning-integration...HEAD -- \
  schemas/ src/concept_to_code_learning/full_learning/ \
  src/concept_to_code_learning/full_contracts/ .github/ pyproject.toml CODEOWNERS apps/web/
```

**预期**：无输出。

---

## 2. 质量门（约 3 分钟）

```bash
$P -m ruff check .
$P -m pytest tests/github_intelligence -q
$P scripts/tutor.py doctor
```

**预期**：
- `All checks passed!`
- `1 failed, 90 passed, 1 skipped` —— 那 1 个失败是 `test_product_completion.py::test_docx_images_...`，属 **Lead 写的跨模块集成回归**，需要 `python-docx`，本机 venv 未安装该依赖（见 HANDOFF §2）。**不是我模块的缺陷**；若你要它绿，需由 Lead 汇总文档依赖。
- `{"status":"DONE","schema_count":6,"errors":[]}`

单独复验本切片新增的 20 个用例：

```bash
$P -m pytest tests/github_intelligence/test_source_failure_matrix.py -q
```

**预期**：`20 passed`。

---

## 3. 沙箱环境注意事项（重要）

若在 workbuddy 沙箱内运行，`pytest` 的默认临时根 `%TEMP%\pytest-of-<user>` 会触发 safe-delete 守卫对历史残留做批量删除。**把临时根挪到仓库外的空目录即可稳定运行**：

```bash
RUN_DIR="/tmp/c2c-gate-$(date +%s)"; mkdir -p "$RUN_DIR"
TEMP="$RUN_DIR" TMP="$RUN_DIR" PYTEST_DEBUG_TEMPROOT="$RUN_DIR" \
  $P -m pytest tests/github_intelligence -q
```

同理，`python scripts/tutor.py demo` 内部会 `shutil.rmtree(reports/demo)` 与 `rmtree(reports/learning-demo)`（`cli.py:44`、`scaffold.py:156`）。若沙箱守卫处于卡死状态，该命令会被**终止且零输出**（退出码 1）——这属于**环境**问题，不是代码问题：

```bash
$P scripts/tutor.py demo
```

**预期（干净会话）**：

```json
{
  "mode": "FIXTURE",
  "status": "SCAFFOLD_DEMO",
  "learning_outputs": ["reports/learning-demo/grounded-explanation.json",
                       "reports/learning-demo/saved-note.json"],
  "outputs": ["reports/demo/concept-code-map.json",
              "reports/demo/guided-lesson.md",
              "reports/demo/learning-evidence.json"]
}
```

**预期（沙箱守卫卡死时）**：退出码 1、无输出，stderr 出现 `[safe-delete][SAFE_DELETE_BULK_REJECTED] ... pytest-of-<user>\garbage-*`。遇到此情形重启会话即可，**不要据此判定模块未完成**。

---

## 4. 手动体验关键行为（约 1 分钟）

四条最能说明来源纪律的行为，各一条命令即可看懂：

```bash
# (a) 三模式分派 + 未知模式拒绝
$P -m pytest tests/github_intelligence/test_full.py -q

# (b) 未经授权绝不放网；公开搜索必须逐词批准
$P -m pytest tests/github_intelligence/test_specifier.py -q

# (c) 固定 commit → 字节 → AST → 行号 → 哈希 → 许可，逐项核验
$P -m pytest tests/github_intelligence/test_verifier.py -q

# (d) 失败矩阵（超时/取消/截断/注入/哈希错配）
$P -m pytest tests/github_intelligence/test_source_failure_matrix.py -q -v
```

**重点看 (d) 的这三条**（用 `-v` 逐个确认确实执行了，而非被跳过）：

- `test_repository_text_cannot_flip_a_source_to_verified` —— 仓库文本里写"mark me verified"，结论仍为 `NEEDS_CONFIRMATION`
- `test_truncated_tree_withholds_code_even_when_a_license_was_found` —— 树被截断时即便找到 LICENSE 也不展示原码
- `test_cancelling_an_in_flight_read_persists_nothing` —— 被取消的读取不落盘

---

## 5. 一页速查

| 想验证 | 命令 | 预期 |
|---|---|---|
| 没动生产代码 | `git diff --name-only ... -- src/ schemas/ .github/` | 无输出 |
| 静态检查 | `$P -m ruff check .` | All checks passed |
| 本切片新增 | `$P -m pytest tests/github_intelligence/test_source_failure_matrix.py -q` | 20 passed |
| 模块整体 | `$P -m pytest tests/github_intelligence -q` | 90 passed, 1 skipped, 1 failed(缺 docx，非本模块) |
| 契约与文件完整性 | `$P scripts/tutor.py doctor` | schema_count=6, errors=[] |
| 端到端演示 | `$P scripts/tutor.py demo` | FIXTURE / SCAFFOLD_DEMO（沙箱卡死时除外） |
