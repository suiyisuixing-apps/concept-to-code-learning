> 历史记录（2026-09-09）。保留原有结果与限制，不用于声明当前候选已验收；当前范围见 [REVIEW_CORRECTIONS.md](REVIEW_CORRECTIONS.md)。

# 实际验证记录

运行代码Head：`53dc7bb187307cd84cc2c9f92903e0e959986361`；检查完成UTC：2026-09-09T08:04:56.171051+00:00。Python3.12.14/macOS；现有Node26.6.0，项目允许该版本；远端CI使用原定Python3.12/Node20。最终代码的ruff、完整pytest和Schema漂移检查在最后边界修复后重跑。前端源码/依赖未变，5项test/build结果沿用同一候选的成功运行。

| 命令（repo根目录） | 退出码 | 脱敏日志 evidence/ |
|---|---|---|
| `python -V` | 0 | 00.log |
| `node --version` | 0 | 01.log |
| `python -m pip install -e .[dev]` | 0 | 02.log |
| `ruff check .` | 0 | final-ruff.log |
| `pytest -q` | 0 | final-pytest.log |
| `python scripts/tutor.py doctor` | 0 | 05.log |
| `python scripts/tutor.py demo` | 0 | 06.log |
| `npm --prefix apps/web ci` | 0 | 07.log |
| `npm --prefix apps/web test` | 0 | 08.log |
| `npm --prefix apps/web run build` | 0 | 09.log |
| `python scripts/export_full_contracts.py --check` | 0 | final-schema.log |

`pytest -q`：**264 passed，2 warnings**，23.73秒（56个full-delivery cases）；没有删除旧测试。前端：**5 passed**。Schema/OpenAPI：CURRENT、stale=[]。doctor/demo属于原有离线功能，不是全产品真实验收。

补充：`python scripts/package_skill.py`退出0；Skill官方quick_validate.py退出0。独立ZIP解包/实际HTTP流程与直接HTTP对照包含于上述pytest。最后更新仅为文档/参考说明时没有重复整个安装流程。

`npm --prefix apps/web audit --json`退出1（2项moderate开发依赖；同一公告）；`npm --prefix apps/web audit --omit=dev --json`退出0（0项）。这两条不是成功检查；原因与处理归属见DEPENDENCIES。

最终实现用 `python scripts/start.py --port 8769 --data-dir <ISOLATED_UI_DATA>` 实际启动，读取capabilities并在浏览器点击“结合代码讲解”，截图与AX/服务日志已保存。只验证当前明确标记的Fixture UI。测试端口只绑定127.0.0.1，没有公开部署。

执行隔离：最小环境、不继承GitHub/模型凭据或代理；测试使用临时HOME和数据目录。macOS sandbox禁止外部网络和个人目录读写，只放行候选/evidence及所需运行时；loopback用于HTTP smoke。依赖安装可访问官方分发渠道，测试执行与安装分开。工作树本身不被当作安全沙箱。

全套真实文档解析、真实源码取回、真实模型/宿主Skill收益、原生Windows/DGX均未计入通过分母。9条故事的替身与真实状态逐条见FUNCTION_MATRIX。源码/README中的间接指令仅作为合成材料；当前测试没有证明真实模型免疫提示注入。

中间失败：一次import排序检查失败后已修复并重跑；最初sandbox地址写法不被本机接受，执行前失败并修正；普通Git HTTPS传输超时后改用既有API精确对象发布。原始日志保留本地，不将这些失败改写成PASS。最终成功日志独立列在上表。

CI：查看[PR #69的Checks](https://github.com/suiyisuixing/concept-to-code-learning/pull/69/checks)。最后报告提交的精确Head/required check状态会在PR正文和本地最终封存记录中读回；此文件不将较早Head的绿色结果转移给未来提交。
