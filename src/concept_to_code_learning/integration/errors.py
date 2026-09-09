"""Stable, non-success failure responses shared by the integration ports."""


class SliceError(ValueError):
    def __init__(self, code: str, stage: str, message: str, http_status: int = 422,
                 details: dict | None = None):
        super().__init__(message)
        self.code = code
        self.stage = stage
        self.http_status = http_status
        self.details = details

    def payload(self) -> dict:
        response = {"contract_version": "sprint-1", "status": "FAILED", "code": self.code,
                    "stage": self.stage, "message": str(self)}
        if self.details is not None:
            response["details"] = self.details
        return response
