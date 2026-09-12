"""Load only installed, Lead-reviewed member entrypoints. Missing modules fail visibly."""

import importlib
import json
import os
from dataclasses import dataclass, field, replace
from pathlib import Path
from urllib.parse import urlsplit

from concept_to_code_learning.full_contracts.models import ProviderCapability
from concept_to_code_learning.full_learning.errors import LearningError
from concept_to_code_learning.full_learning.ports import ProviderBundle


@dataclass(frozen=True)
class ProviderSettings:
    root: Path
    data_dir: Path
    contract_version: str = "full-delivery-v1"
    max_document_bytes: int = 20 * 1024 * 1024
    github_token: str | None = field(default=None, repr=False)
    model_base_url: str | None = field(default=None, repr=False)
    model_id: str | None = None
    model_api_key: str | None = field(default=None, repr=False)
    model_network_authorized: bool = False
    authorized_local_roots: tuple[Path, ...] = field(default=(), repr=False)
    model_structured_output: bool = False

    @classmethod
    def from_env(cls, root: Path, data_dir: Path):
        endpoint = os.environ.get("C2C_MODEL_BASE_URL") or None
        authorized = os.environ.get("C2C_MODEL_NETWORK_AUTHORIZED") == "1"
        if endpoint:
            url = urlsplit(endpoint)
            local = url.hostname in {"127.0.0.1", "localhost", "::1"}
            if (url.scheme not in {"http", "https"} or not url.hostname
                    or url.username or url.password or url.query or url.fragment
                    or not local and url.scheme != "https"
                    or not local and not authorized):
                raise LearningError("INVALID_CONFIGURATION", "configuration",
                                    "模型端点不合法或缺少明确远程数据授权。")
        try:
            paths = json.loads(os.environ.get("C2C_LOCAL_ROOTS_JSON", "[]"))
            if not isinstance(paths, list) or not all(isinstance(p, str) for p in paths):
                raise ValueError
            roots = tuple(Path(path).expanduser().resolve(strict=True) for path in paths)
            if not all(path.is_dir() for path in roots):
                raise ValueError
        except (OSError, ValueError) as exc:
            raise LearningError("INVALID_CONFIGURATION", "configuration",
                                "本地仓库授权列表必须是已存在目录的 JSON 数组。") from exc
        # Deliberately do not inherit GH_TOKEN, gh's owner credential or arbitrary host keys.
        return cls(root, data_dir, github_token=os.environ.get("C2C_GITHUB_TOKEN") or None,
                   model_base_url=endpoint, model_id=os.environ.get("C2C_MODEL_ID") or None,
                   model_api_key=os.environ.get("C2C_MODEL_API_KEY") or None,
                   model_network_authorized=authorized, authorized_local_roots=roots,
                   model_structured_output=os.environ.get("C2C_MODEL_STRUCTURED_OUTPUT") == "1")


class UnavailableProvider:
    def __init__(self, role: str, code: str = "MODULE_NOT_DELIVERED"):
        self.role, self.code = role, code

    async def capabilities(self):
        return ProviderCapability(provider_id=self.role, implemented=False, available=False,
                                  mode="UNAVAILABLE", features=[], status="UNAVAILABLE",
                                  reason_code=self.code,
                                  needed_action="接入该角色的完整模块并完成配置与实测。")

    async def close(self):
        return None

    def __getattr__(self, name):
        async def unavailable(*args, **kwargs):
            code = "MODEL_NOT_CONFIGURED" if self.role == "tutor" else self.code
            raise LearningError(code, self.role, "对应真实模块尚未接入或未完成配置。", 503,
                                needed_action="检查 capabilities；接入模块后重试。")
        return unavailable


def build_providers(settings: ProviderSettings) -> ProviderBundle:
    entries = {
        "document": "concept_to_code_learning.documents.full",
        "sources": "concept_to_code_learning.github_intelligence.full",
        "tutor": "concept_to_code_learning.tutor.full",
    }
    providers = {}
    for role, module_name in entries.items():
        try:
            module = importlib.import_module(module_name)
            scoped = replace(settings,
                github_token=settings.github_token if role == "sources" else None,
                model_base_url=settings.model_base_url if role == "tutor" else None,
                model_api_key=settings.model_api_key if role == "tutor" else None,
                model_id=settings.model_id if role == "tutor" else None,
                model_network_authorized=settings.model_network_authorized if role == "tutor" else False,
                model_structured_output=settings.model_structured_output if role == "tutor" else False,
                authorized_local_roots=settings.authorized_local_roots if role == "sources" else ())
            providers[role] = module.build_provider(scoped)
        except ModuleNotFoundError as exc:
            providers[role] = UnavailableProvider(role, "MODULE_NOT_DELIVERED" if (
                exc.name == module_name) else "DEPENDENCY_MISSING")
        except Exception:
            providers[role] = UnavailableProvider(role, "PROVIDER_LOAD_FAILED")
    return ProviderBundle(**providers)
