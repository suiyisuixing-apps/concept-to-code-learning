# 启动与配置

产品使用 Python 3.12、React/Vite、FastAPI。桌面入口打开本地浏览器，是本机 Web 工作台。

## 一次准备

macOS，在产品目录运行：

```sh
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -c requirements/full-delivery-py312.lock -e ".[dev]"
npm --prefix apps/web ci --ignore-scripts
npm --prefix apps/web run build
python scripts/desktop.py
```

Windows PowerShell：

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -c requirements/full-delivery-py312.lock -e ".[dev]"
npm --prefix apps/web ci --ignore-scripts
npm --prefix apps/web run build
.\.venv\Scripts\python.exe scripts\desktop.py
```

以后只需运行最后一条。默认打开 http://127.0.0.1:8766 ，按 Ctrl+C 停止本次启动的服务。`--port 8770` 可换端口，`--no-browser` 适合终端检查。模型服务占用应用端口加一。端口已被其他程序使用时启动器会报错，不会关闭其他进程。

## 模型连接

设置文件为 macOS `~/Library/Application Support/ConceptToCode/desktop.json`、Windows `%LOCALAPPDATA%/ConceptToCode/desktop.json`、Linux `~/.local/share/concept-to-code/desktop.json`。也可通过 `--config 路径` 指定。

Apple Silicon Mac，使用已安装的 MLX 环境与已下载模型，按 `config/desktop-mlx.example.json` 填写实际路径。`model_python` 指向该虚拟环境的 Python；模型文件留在 Git 之外。本次本机验收采用 Qwen3-4B-Instruct-2507 的 MLX 4bit 版本，约 2.3 GB，固定版本和校验记录见审核材料。启动时关闭在线模型下载与遥测，只监听 127.0.0.1。

连接已有服务（Windows、Linux 或 Mac）使用 `config/desktop-endpoint.example.json`。服务需要 `/v1/models` 和 `/v1/chat/completions`，支持非流式文本返回，模型名必须准确。远程服务需 HTTPS，并且已获授权发送所选文档片段与来源代码，才可设置 `model_network_authorized: true`。SSH 转发到本机的已授权 DGX 可采用 loopback 地址；主机部署见 `deploy/dgx/`。

秘钥仅通过 `C2C_MODEL_API_KEY` / `C2C_GITHUB_TOKEN` 环境变量传入，不写到设置文件或网页。未提供 GitHub token 时仍可读取公开仓库，但受匿名配额限制；限流会明确显示。产品不读取 gh 的管理员凭据。

手动管理已有模型进程时，也可设置以下环境变量后直接运行 `python scripts/start.py`：

| 变量 | 用途 |
|---|---|
| C2C_DATA_DIR | 显式指定数据目录；start 的默认值是 checkout 的 data/local |
| C2C_MODEL_BASE_URL / C2C_MODEL_ID | 模型 API base URL（可带 /v1）和服务提供的准确模型名 |
| C2C_MODEL_API_KEY | 可选模型凭据，只用于模型请求 |
| C2C_MODEL_NETWORK_AUTHORIZED=1 | 明确允许向已选非本机模型发送数据；不授权费用 |
| C2C_GITHUB_TOKEN | 可选专用 GitHub 凭据，仅发给 GitHub API |
| C2C_LOCAL_ROOTS_JSON | 已授权本地 Git 仓库目录的 JSON 数组 |
| C2C_DEV_ORIGIN | 开发前端的明确本机 Origin |

`.env.example` 只是模板，不自动加载。

## 本地仓库

在 desktop.json 的 `local_roots` 中填写自己授权的 Git 仓库目录，然后重启。浏览器只能选择不透明句柄，不能传入任意主机路径。只读取 tracked 源码，忽略子模块/符号链接越界；不会安装或执行仓库脚本。未提交内容以实际字节哈希和 dirty 标记保留，不伪造固定公网链接。

## 保存和恢复

desktop 入口默认在上述应用目录的 `data/` 保存文档副本与 `learning-v1.sqlite3`。可在 desktop.json 中指定 `data_dir`。旧 `fixture-notes.sqlite3` 和旧接口继续兼容，本轮没有迁移或覆盖旧表。

笔记通过用户保存动作创建。修改个人文字会生成新修订，原讲解和来源冻结不变；单条可导出 Markdown/JSON。完整备份前正常停止应用，再复制整个数据目录。恢复时保留当前目录副本，用备份的独立目录启动确认；不要在应用写入中只复制一个 SQLite 文件。

## 常见情况

- 模型尚未配置：阅读和笔记可用；完成配置并重启，或点击重新检查模型。
- GitHub 限流：等待服务提示的窗口后重试，不需要管理员权限。
- 无匹配代码：仍可获得文档讲解，状态为未核验源码。
- 引用校验失败：回答被拒绝，不保存为有据解释；缩短问题/选区后重试。
- 模型超时或输出不完整：保留原问题，缩短上下文，或使用已经授权的更强模型。
- 扫描/空白页：显示没有可提取文字；本版未提供 OCR。
- Office 复杂图表/公式：阅读器显示预览范围，请参照原文件；Word 的章节不是固定物理页。

MLX 上游服务适用于受控本机使用，本版不作为公网推理服务器部署。DGX 包与 Windows 指令已提供；各平台真正完成的检查以 FINAL_REVIEW 的证据表为准。
