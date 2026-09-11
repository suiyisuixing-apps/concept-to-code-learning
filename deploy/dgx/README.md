# DGX / Linux 模型接入

此交付包提供部署入口，**尚未在 DGX 硬件实测**。Mac 上验证的是 Qwen3 4B 的 MLX 量化版；它的权重格式不能直接交给 vLLM。

1. 管理员在既有 Python/CUDA 环境中确认 `nvidia-smi`、`vllm --version`，并根据 [vLLM 官方安装说明](https://docs.vllm.ai/en/latest/getting_started/installation/gpu.html) 核对 GPU/CUDA 兼容性。脚本不会安装驱动、Docker 或下载模型。
2. 选择已授权、已下载、带许可记录的 Hugging Face 格式指令模型。模型代码必须由现有 vLLM 原生支持；不启用 trust-remote-code。
3. 在服务器执行 `python deploy/dgx/start_model.py --model-dir /absolute/model/path`，默认仅监听服务器本机 8001。多 GPU 可设置 `--tensor-parallel-size`。
4. 使用自己已授权的 SSH 连接，将 Mac 的本地端口转发到服务器 `127.0.0.1:8001`。应用配置 `C2C_MODEL_BASE_URL=http://127.0.0.1:8001/v1`、`C2C_MODEL_ID=c2c-tutor`。隧道中的材料仍会离开 Mac 到服务器；使用前确认服务器与该数据用途均获得授权。
5. 运行 `python scripts/model_probe.py --base-url http://127.0.0.1:8001/v1 --model c2c-tutor --output dgx-probe.json`。探针只发送自制中文问题，记录真实用量与响应时间。随后按产品验收记录检查四等级、追问、比较及取消。

通过探针只证明模型协议可用。GPU 内存、长上下文并发、实际课件质量、热稳定性和完整产品验收需在目标硬件另行记录。vLLM 参数依据 [官方 OpenAI 兼容服务文档](https://docs.vllm.ai/en/latest/serving/openai_compatible_server.html)。
