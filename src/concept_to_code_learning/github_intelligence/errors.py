"""Source provider errors. Token never enters messages or logs."""

from __future__ import annotations

from typing import Any


class SourceError(Exception):
    """Structured failure used by search/verify. Caller maps it to learning errors."""

    def __init__(self, code: str, stage: str, message: str, status: int = 503,
                 *, needed_action: str | None = None, detail: dict[str, Any] | None = None):
        super().__init__(message)
        # Codes follow the public B8 vocabulary in INTERFACES.md:
        # NETWORK_NOT_AUTHORIZED / AUTH_REQUIRED / RATE_LIMITED / REPO_UNAVAILABLE
        # / REF_UNRESOLVED / FILE_NOT_FOUND / SYMBOL_NOT_FOUND / SOURCE_MISMATCH
        # / LICENSE_UNKNOWN / NO_RELEVANT_SOURCE / INVALID_PROVIDER_RESPONSE.
        self.code = code
        self.stage = stage
        self.status = status
        self.needed_action = needed_action
        self.detail = detail or {}

    def __str__(self) -> str:
        return f"[{self.code}] {super().__str__()}"

    def to_dict(self) -> dict[str, Any]:
        return {"code": self.code, "stage": self.stage, "message": str(self),
                "status": self.status, "needed_action": self.needed_action,
                "detail": self.detail}


def not_implemented(stage: str, feature: str) -> SourceError:
    """Honest marker for capabilities not yet delivered in this slice."""
    return SourceError("NOT_IMPLEMENTED", stage,
                       f"{feature} is not implemented in the current slice; "
                       f"tracked in docs/delivery/zchzbjklg/HANDOFF.md",
                       status=501, needed_action="Implement the remaining modes in the next slice.")
