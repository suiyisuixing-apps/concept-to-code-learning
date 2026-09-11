"""Public errors never include raw provider messages, tokens or private paths."""

from concept_to_code_learning.full_contracts.models import LearningErrorResponse, uid


class LearningError(Exception):
    def __init__(self, code: str, stage: str, message: str, status: int = 422,
                 *, retryable: bool = False, needed_action: str | None = None):
        super().__init__(code)
        self.code, self.stage, self.message = code, stage, message
        self.http_status, self.retryable, self.needed_action = status, retryable, needed_action

    def payload(self, request_id: str | None = None) -> dict:
        return LearningErrorResponse(request_id=request_id or uid(), stage=self.stage,
                                     code=self.code, user_message=self.message,
                                     retryable=self.retryable,
                                     needed_action=self.needed_action).model_dump(mode="json")


def require(condition: bool, code: str, stage: str, message: str, status: int = 422):
    if not condition:
        raise LearningError(code, stage, message, status)
