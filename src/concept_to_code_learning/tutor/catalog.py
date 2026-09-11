"""Request-scoped selection among models actually served by an authorized endpoint."""

import time
from dataclasses import replace
from urllib.parse import urlsplit

from pydantic import Field

from concept_to_code_learning.full_contracts.models import Value
from concept_to_code_learning.full_learning.errors import LearningError, require
from concept_to_code_learning.runtime.async_model import AsyncLocalModelAdapter
from concept_to_code_learning.runtime.local_model import LocalModelConfig, is_loopback_host
from concept_to_code_learning.tutor.full import GroundedTutorProvider


class ModelEndpoint(Value):
    base_url: str | None = Field(default=None, max_length=500)


class ModelOption(Value):
    id: str
    name: str


class ModelList(Value):
    models: list[ModelOption]
    default_model: str | None = None
    base_url: str | None = None


class TutorCatalog:
    def __init__(self, default):
        self.default = default
        self.config = getattr(default, "config", None)
        if not isinstance(self.config, LocalModelConfig):
            self.config = None
        self.providers = {}
        self.inventory = {}

    def configuration(self, endpoint=None):
        if not endpoint or self.config and endpoint.rstrip("/") == self.config.base_url.rstrip("/"):
            require(
                self.config is not None,
                "MODEL_NOT_CONFIGURED",
                "model",
                "连接一个本地模型服务后再选择模型。",
                503,
            )
            return self.config
        parsed = urlsplit(endpoint)
        require(
            parsed.scheme in {"http", "https"}
            and is_loopback_host(parsed.hostname)
            and not parsed.username
            and not parsed.password
            and not parsed.query
            and not parsed.fragment
            and parsed.path.rstrip("/") in {"", "/v1"},
            "INVALID_MODEL_ENDPOINT",
            "model",
            "请输入本机模型服务地址，例如 http://127.0.0.1:11434/v1。",
        )
        return LocalModelConfig(
            endpoint.rstrip("/"),
            "model-discovery",
            timeout_seconds=60,
            max_output_tokens=2500,
            max_input_chars=24000,
            max_retries=0,
        )

    async def discover(self, endpoint=None, *, cached=False):
        if endpoint is None and self.config is None:
            return ModelList(models=[])
        config = self.configuration(endpoint)
        previous = self.inventory.get(config.base_url)
        if cached and previous and time.monotonic() - previous[0] < 10:
            return previous[1]
        adapter = AsyncLocalModelAdapter(replace(config, timeout_seconds=5))
        try:
            result = await adapter.models()
        finally:
            await adapter.close()
        if not result.ok:
            raise LearningError(
                result.error_code or "MODEL_OFFLINE",
                "model",
                "没有连接到模型服务。请确认地址和服务状态后重试。",
                503,
                retryable=True,
            )
        value = ModelList(
            models=[
                ModelOption(id=item, name=item.replace("\\", "/").rsplit("/", 1)[-1])
                for item in result.usage["served_models"]
            ],
            default_model=config.model if config.model in result.usage["served_models"] else None,
            base_url=config.base_url,
        )
        if len(self.inventory) >= 16:
            self.inventory.pop(next(iter(self.inventory)))
        self.inventory[config.base_url] = (time.monotonic(), value)
        return value

    async def resolve(self, model_id=None, endpoint=None):
        if model_id is None and endpoint is None:
            return self.default
        config = self.configuration(endpoint)
        model_id = model_id or config.model
        available = await self.discover(endpoint, cached=True)
        require(
            model_id in {item.id for item in available.models},
            "MODEL_NOT_FOUND",
            "model",
            "这个服务已不再提供所选模型，请重新选择。",
            422,
        )
        if self.config and (config.base_url, model_id) == (self.config.base_url, self.config.model):
            return self.default
        key = config.base_url, model_id
        if key not in self.providers:
            require(
                len(self.providers) < 16,
                "MODEL_LIMIT_REACHED",
                "model",
                "本次已连接较多模型，请重启工作台后再添加。",
            )
            selected = replace(config, model=model_id)
            self.providers[key] = GroundedTutorProvider(AsyncLocalModelAdapter(selected), selected)
        return self.providers[key]

    async def close(self):
        for provider in self.providers.values():
            await provider.close()
