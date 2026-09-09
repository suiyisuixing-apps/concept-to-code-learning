# 依赖、平台与许可观察

本轮按原 checkout 已安装且通过的实际版本固定 Python 共同基线，没有整体升级框架。Python要求仍 >=3.12,<3.13；本机3.12.14。前端 package.json/package-lock.json 未更改；CI仍Node20，本机已有Node26.6.0在其engines范围内。没有下载新Node/Python主版本或模型。

Python直接运行依赖固定：jsonschema4.26.0、fastapi0.141.1、uvicorn0.52.4、pydantic2.13.5、starlette1.6.0。Pydantic/Starlette原已由FastAPI引入，当前代码直接使用因此显式列出。开发依赖固定 pytest9.1.1、ruff0.16.6、PyYAML6.0.3、httpx0.28.1。

完整28项已安装distribution版本与许可元数据见 dependencies.json；约束快照见 requirements/full-delivery-py312.lock。它是本次Python3.12环境快照，不是全平台带哈希下载锁。原生Windows可能还解析平台条件依赖，必须在Windows补记录；不把Mac解析结果当成Windows已安装证据。三个成员尚无完整新依赖清单可合并，其到位后由Lead再汇总。

许可是已安装METADATA的观察值（MIT/BSD/Apache/PSF，以及certifi的MPL-2.0等），不是法律审查结论。没有因未知项猜许可证。产品代码来源许可另由来源模块逐Commit记录，不能继承这些包的许可结论。

## npm审计

完整npm audit退出1：2项moderate（Vitest3.2.7与其@vitest/mocker，属于同一份公告，不是两种独立漏洞）。生产依赖 `npm audit --omit=dev --json` 退出0、0项报告。报告见 evidence/npm-audit*.json。

[Vitest官方公告 GHSA-82fw-gwwq-j7x9](https://github.com/vitest-dev/vitest/security/advisories/GHSA-82fw-gwwq-j7x9)描述开发服务器公开mocker/interceptor插件的任意文件读取路径；修复在4.1.11及后续。当前vite.config.js只注册React插件，测试用jsdom的vitest run，未接入这些公开插件/浏览器模式；发布入口由FastAPI提供静态dist。本次源码检查没有发现公告所需的公开开发服务路径，因此不据依赖扫描直接断言产品可远程利用。

告警仍保留，属于待处理开发依赖风险。需要跨Vitest主版本，按本次授权不运行 npm audit fix --force 或替inogi整体升级前端；由#66记录升级理由、兼容验证后由Lead接纳。不要将该开发服务器暴露到公网。没有运行攻击载荷、第三方项目脚本、增加付费服务、试用或付款方式；账单余额没有被独立审计。

npm ci另有whatwg-encoding弃用提示和esbuild/fsevents安装脚本政策提示；此次build成功，不称为警告全清除。Python测试的2项Starlette/httpx与anyio弃用警告也保留，未通过更换测试库或删测试消除。
