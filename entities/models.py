"""Framework-independent values for the CAPTCHA application."""
from dataclasses import dataclass


@dataclass(frozen=True)
class CustomerIdentity:
    customer_id: int
    key_id: int
    monthly_quota: int
    rate_limit_per_min: int


@dataclass(frozen=True)
class SolveCommand:
    bearer_token: str
    captcha_type: str
    content: bytes
    correlation_id: str


@dataclass(frozen=True)
class SolveResult:
    prediction: str
    captcha_type: str
    processing_time_ms: int
    correlation_id: str


class ApplicationError(Exception):
    """A controlled error whose status may be shown to the client."""

    def __init__(self, message: str, status: int, code: str):
        super().__init__(message)
        self.status = status
        self.code = code
