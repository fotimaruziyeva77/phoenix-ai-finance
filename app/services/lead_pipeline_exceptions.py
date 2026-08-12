"""Domain errors for owner-scoped CRM pipeline operations on leads."""

from __future__ import annotations

from typing import ClassVar


class LeadPipelineServiceError(Exception):
    status_code: ClassVar[int] = 400
    code: ClassVar[str] = "lead_pipeline_error"
    default_message: ClassVar[str] = "Lead pipeline operation failed"

    def __init__(self, message: str | None = None) -> None:
        self.message = message or self.default_message
        super().__init__(self.message)


class LeadNotFoundError(LeadPipelineServiceError):
    status_code = 404
    code = "lead_not_found"
    default_message = "Lead was not found"


class LeadPipelineValidationError(LeadPipelineServiceError):
    status_code = 422
    code = "lead_pipeline_validation_error"
    default_message = "Lead pipeline payload is invalid"


class LeadInvalidStatusTransitionError(LeadPipelineServiceError):
    """Business rule: e.g. leaving terminal won/lost."""

    status_code = 409
    code = "lead_invalid_status_transition"
    default_message = "This status change is not allowed"


__all__ = [
    "LeadInvalidStatusTransitionError",
    "LeadNotFoundError",
    "LeadPipelineServiceError",
    "LeadPipelineValidationError",
]
