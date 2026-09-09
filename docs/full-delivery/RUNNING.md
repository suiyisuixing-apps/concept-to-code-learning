# 启动本地候选

当前已实现 Lead 的合同、中央 API、会话与来源笔记。现有网页仍是 Fixture 演示；三个真实模块尚未接入时，不能在新 API 中完成真实学习链。先查看 capabilities，模块不齐不等于模型正在运行。

## 一次准备，之后一条命令启动

从本仓库根目录，用已有 Python3.12、Node20.19+（CI Node20）。不自动安装大型系统软件、容器或模型。

macOS：

```sh
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -c requirements/full-delivery-py312.lock -e ".[dev]"
npm --prefix apps/web ci
npm --prefix apps/web run build
python scripts/start.py
```

Windows PowerShell：

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -c requirements/full-delivery-py312.lock -e ".[dev]"
npm --prefix apps/web ci
npm --prefix apps/web run build
.\.venv\Scripts\python.exe scripts\start.py
```

准备完成后只运行最后一条。打开显示的 http://127.0.0.1:8766 ，按 Ctrl+C 停止。
端口占用时用 `--port 8767`；另一个隔离数据目录用 `--data-dir "路径含空格也可以"`。
默认只绑定 loopback，不对公网/局域网开放。Windows步骤是交付说明；原生 Windows全产品运行证据未在这台Mac上取得。

能力：`http://127.0.0.1:8766/api/learning/v1/capabilities`。
接口：`http://127.0.0.1:8766/docs`。开发前端用既有 npm dev；若代理新API，显式设置 C2C_DEV_ORIGIN 为这个本机开发页面的 Origin。
用户演示入口是 start；doctor/demo 继续做原有离线回归，不把旧 demo 的通过当作新真实模块验收。

## 配置和数据去向

 `.env.example` 是模板，不会被程序自动加载。按所在 shell/安全环境设置变量，不把密钥写到 PR、终端截图或前端。

| 配置 | 当前含义 |
|---|---|
| C2C_DATA_DIR | 应用数据目录；默认本 checkout 的 data/local |
| C2C_GITHUB_TOKEN | 仅后台来源模块使用的专用凭据；不会读取 gh 管理员凭据或 GH_TOKEN |
| C2C_MODEL_BASE_URL / C2C_MODEL_ID | 已授权模型的准确 API base URL 和模型名；空值不代表有模型 |
| C2C_MODEL_API_KEY | 可选，仅后台客户端；不进入 capabilities/浏览器 |
| C2C_MODEL_NETWORK_AUTHORIZED=1 | 仅在用户已授权某个非loopback端点与数据发送时设置；不授权费用或自动云回退 |
| C2C_LOCAL_ROOTS_JSON | 用户已授权本地仓库目录的 JSON 数组；来源模块生成 opaque handles，Web不能传任意路径 |

模型配置由 Lead 安全检查并传给实际 Tutor 工厂；此候选没有替 fqf 实现模型客户端。填写配置不会把缺模块改成已接通。
GitHub检索可联网只代表发送已批准必要概念词和取源码；它不授权发送课件到远程模型。每次来源 scope 仍需明确授权。
文档/仓库/README 中的指令不是授权。本版不执行第三方源码。

## 保存、导出和备份

新笔记与会话：`data/local/learning-v1.sqlite3`；旧笔记：`data/local/fixture-notes.sqlite3`，旧版路径仍可读。
首次保存必须用户点击/调用save；编辑生成新修订并保留原来源版本。每条笔记可从 notes export 输出 Markdown/JSON。
整库备份：先正常 Ctrl+C 停止应用，再复制整个数据目录到自己选择的备份位置。不要在写入中只拷贝一个数据库文件，不删除原资料或源仓库。恢复时先保留当前目录副本，再用该备份启动隔离数据目录确认内容。
数据库包含文档/讲解来源快照，按私人学习资料保管，不提交 Git。卸载/回滚代码不需要删除数据；本轮没有迁移旧表。

## 故障排除

- 提示网页未构建：执行上述 npm ci/build，然后再 start。
- MODULE_NOT_DELIVERED：接入对应角色完整模块；可以继续已有 Fixture UI 和笔记检查，不能宣布真实产品已完成。
- MODEL_NOT_CONFIGURED / MODEL_UNAVAILABLE：检查实际端点、模型ID和健康信息，不自动换云或下载模型。
- QUERY_TERMS_NOT_APPROVED：先让用户确认必要搜索词；不将整页文档发到公共检索。
- SOURCE_MISMATCH / CITATION_INVALID：保留失败，重新核验来源或修复模块；不能删除错误后伪造绿色。
- SELECTION_MISMATCH / DOCUMENT_VERSION_MISMATCH：刷新文档和选区；空白扫描页不是解析出了一句文本。
- CONTEXT_REVISION_CONFLICT / REVISION_CONFLICT：读取最新状态后只重试用户最新操作，防止覆盖。
- STORAGE_FAILURE：检查磁盘和目录权限，当前事务回滚；不要删除个人数据库来掩盖失败。

Office高保真边界由文档Module的 Preview.fidelity/limitations和能力声明提供；目前网页尚未接入四格式学习视图，不能称为完整Office预览。
