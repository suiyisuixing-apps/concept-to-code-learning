"""Start the built workbench and an already-installed local MLX model. No downloads."""

import argparse
import json
import os
import signal
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def app_directory():
    if sys.platform == "darwin":
        return Path.home() / "Library/Application Support/ConceptToCode"
    if os.name == "nt":
        return Path(os.environ.get("LOCALAPPDATA", Path.home())) / "ConceptToCode"
    return Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share")) / "concept-to-code"


def available_port(port):
    with socket.socket() as sock:
        try:
            sock.bind(("127.0.0.1", port))
        except OSError:
            raise ValueError(
                f"端口 {port} 已被占用。请关闭之前的本应用窗口或改用其他端口。"
            ) from None


def read_json(url):
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(url, timeout=2) as response:
        return json.load(response)


def wait_ready(url, processes, timeout=45):
    until = time.monotonic() + timeout
    while time.monotonic() < until:
        if any(process.poll() is not None for process in processes):
            raise ValueError("应用进程提前退出，请查看本地日志。")
        try:
            return read_json(url)
        except (OSError, ValueError, urllib.error.URLError):
            time.sleep(0.25)
    raise ValueError("本地服务启动超时，请查看本地日志。")


def main(argv=None):
    directory = app_directory()
    parser = argparse.ArgumentParser(description="启动文档学习工作台")
    parser.add_argument("--config", type=Path, default=directory / "desktop.json")
    parser.add_argument("--port", type=int, default=8766)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args(argv)
    if not 1024 <= args.port <= 65533:
        parser.error("端口需为 1024 到 65533。")
    processes, logs = [], []
    try:
        config = json.loads(args.config.read_text(encoding="utf-8")) if args.config.exists() else {}
        if not (ROOT / "apps/web/dist/index.html").is_file():
            raise ValueError("缺少网页构建文件，请先运行 npm --prefix apps/web run build。")
        available_port(args.port)
        data = Path(config.get("data_dir", directory / "data")).expanduser().resolve()
        data.mkdir(parents=True, exist_ok=True)
        logdir = directory / "logs"
        logdir.mkdir(parents=True, exist_ok=True)
        env = {
            k: v
            for k, v in os.environ.items()
            if k
            in {
                "PATH",
                "HOME",
                "TMPDIR",
                "LANG",
                "LC_ALL",
                "SYSTEMROOT",
                "WINDIR",
                "TEMP",
                "TMP",
                "C2C_GITHUB_TOKEN",
                "C2C_MODEL_API_KEY",
            }
        }
        env.update(C2C_DATA_DIR=str(data), PYTHONIOENCODING="utf-8")
        if config.get("local_roots"):
            env["C2C_LOCAL_ROOTS_JSON"] = json.dumps(config["local_roots"])
        model_dir = config.get("model_dir")
        if model_dir:
            model = Path(model_dir).expanduser().resolve(strict=True)
            # Keep the virtual environment entry point; resolving its symlink loses its packages.
            python = Path(config["model_python"]).expanduser().absolute()
            if not python.is_file():
                raise ValueError("指定的本地模型运行环境不存在。")
            if sys.platform != "darwin" or not (model / "model.safetensors").is_file():
                raise ValueError("此本地 MLX 启动方式需要 Apple Silicon Mac 与已下载的模型。")
            available_port(args.port + 1)
            model_env = {k: v for k, v in env.items() if not k.startswith("C2C_")}
            cache = directory / "model-cache"
            (cache / "hub").mkdir(parents=True, exist_ok=True)
            model_env.update(
                HF_HOME=str(cache),
                HF_HUB_OFFLINE="1",
                TRANSFORMERS_OFFLINE="1",
                HF_HUB_DISABLE_TELEMETRY="1",
            )
            model_log = (logdir / "model.log").open("a", encoding="utf-8")
            logs.append(model_log)
            processes.append(
                subprocess.Popen(
                    [
                        str(python),
                        "-m",
                        "mlx_lm",
                        "server",
                        "--model",
                        str(model),
                        "--host",
                        "127.0.0.1",
                        "--port",
                        str(args.port + 1),
                        "--allowed-origins",
                        f"http://127.0.0.1:{args.port}",
                        "--decode-concurrency",
                        "1",
                        "--prompt-concurrency",
                        "1",
                        "--prompt-cache-size",
                        "2",
                        "--prefill-step-size",
                        "512",
                        "--max-tokens",
                        "2500",
                        "--log-level",
                        "WARNING",
                    ],
                    env=model_env,
                    stdout=model_log,
                    stderr=subprocess.STDOUT,
                )
            )
            endpoint = f"http://127.0.0.1:{args.port + 1}/v1"
            models = wait_ready(endpoint + "/models", processes)
            # The startup model and the preferred chat model may differ. The
            # service also lists pinned models in this app's offline cache.
            selected_model = config.get("model_id") or str(model)
            if selected_model not in [x.get("id") for x in models.get("data", [])]:
                raise ValueError("模型服务没有提供指定的模型。")
            env.update(C2C_MODEL_BASE_URL=endpoint, C2C_MODEL_ID=selected_model)
        elif config.get("model_base_url"):
            env.update(C2C_MODEL_BASE_URL=config["model_base_url"], C2C_MODEL_ID=config["model_id"])
            if config.get("model_structured_output") is True:
                env["C2C_MODEL_STRUCTURED_OUTPUT"] = "1"
            if config.get("model_network_authorized") is True:
                env["C2C_MODEL_NETWORK_AUTHORIZED"] = "1"
        app_log = (logdir / "application.log").open("a", encoding="utf-8")
        logs.append(app_log)
        processes.append(
            subprocess.Popen(
                [sys.executable, str(ROOT / "scripts/start.py"), "--port", str(args.port)],
                env=env,
                stdout=app_log,
                stderr=subprocess.STDOUT,
            )
        )
        url = f"http://127.0.0.1:{args.port}"
        wait_ready(url + "/api/learning/v1/capabilities", processes)
        print(
            f"学习工作台已启动：{url}\n笔记保存在：{data}\n按 Ctrl+C 关闭本次启动的服务。",
            flush=True,
        )
        if not args.no_browser:
            webbrowser.open(url)
        return processes[-1].wait()
    except KeyboardInterrupt:
        return 0
    except (OSError, ValueError, KeyError) as exc:
        print(f"启动未完成：{exc}", file=sys.stderr)
        return 1
    finally:
        for process in reversed(processes):
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=8)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
        for log in logs:
            log.close()


def terminate(*_):
    raise KeyboardInterrupt


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, terminate)
    raise SystemExit(main())
