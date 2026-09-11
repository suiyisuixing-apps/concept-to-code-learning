"""Launch an already-installed vLLM against an already-downloaded model on loopback."""

import argparse
import os
import shutil
import subprocess
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-dir", required=True, type=Path)
    parser.add_argument("--port", type=int, default=8001)
    parser.add_argument("--tensor-parallel-size", type=int, default=1)
    parser.add_argument("--max-model-len", type=int, default=8192)
    args = parser.parse_args()
    model = args.model_dir.resolve(strict=True)
    if not model.is_dir() or not (model / "config.json").is_file():
        parser.error("model-dir must contain already-downloaded model files")
    if not 1024 <= args.port <= 65535 or not 1 <= args.tensor_parallel_size <= 8:
        parser.error("invalid port or parallel size")
    if not 4096 <= args.max_model_len <= 32768:
        parser.error("max-model-len must be 4096..32768")
    executable = shutil.which("vllm")
    if not executable:
        parser.error(
            "vLLM is not installed in the active environment; no automatic install was attempted"
        )
    env = {
        k: v
        for k, v in os.environ.items()
        if k in {"PATH", "HOME", "LD_LIBRARY_PATH", "CUDA_VISIBLE_DEVICES", "VIRTUAL_ENV", "LANG"}
    }
    env.update(HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1", HF_HUB_DISABLE_TELEMETRY="1")
    return subprocess.call(
        [
            executable,
            "serve",
            str(model),
            "--served-model-name",
            "c2c-tutor",
            "--host",
            "127.0.0.1",
            "--port",
            str(args.port),
            "--dtype",
            "auto",
            "--tensor-parallel-size",
            str(args.tensor_parallel_size),
            "--max-model-len",
            str(args.max_model_len),
        ],
        env=env,
    )


if __name__ == "__main__":
    raise SystemExit(main())
