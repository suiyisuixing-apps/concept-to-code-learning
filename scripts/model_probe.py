"""Probe an explicitly configured model with a synthetic Chinese question only."""

import argparse
import asyncio
import json
import sys
from dataclasses import asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


def main():
    from concept_to_code_learning.runtime.async_model import AsyncLocalModelAdapter
    from concept_to_code_learning.runtime.local_model import LocalModelConfig

    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--authorized-remote", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    async def probe():
        adapter = AsyncLocalModelAdapter(
            LocalModelConfig(
                args.base_url,
                args.model,
                allow_remote_endpoint=args.authorized_remote,
                timeout_seconds=60,
                max_retries=0,
            )
        )
        health = await adapter.health()
        result = (
            await adapter.generate(
                [{"role": "user", "content": "请用两句中文说明依赖注入，别声称运行过代码。"}]
            )
            if health.ok
            else health
        )
        args.output.write_text(
            json.dumps(
                {
                    "synthetic_input": True,
                    "health": asdict(health),
                    "generation": asdict(result),
                    "hardware_acceptance": "NOT_ASSESSED",
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        return 0 if result.ok else 1

    return asyncio.run(probe())


if __name__ == "__main__":
    raise SystemExit(main())
