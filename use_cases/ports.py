"""Contracts implemented by infrastructure adapters."""
from typing import Protocol
from entities.models import CustomerIdentity


class AuthenticationPort(Protocol):
    def identify(self, bearer_token: str) -> CustomerIdentity | None: ...


class SolverPort(Protocol):
    def solve(self, captcha_type: str, content: bytes) -> str: ...


class RequestStorePort(Protocol):
    def available_adapter(self, captcha_type: str) -> int | None: ...
    def reserve(self, identity: CustomerIdentity, captcha_type: str, adapter_id: int, correlation_id: str) -> int: ...
    def complete(self, request_id: int, status: str, prediction: str | None, duration_ms: int, error: str | None) -> None: ...


class EventPort(Protocol):
    def record(self, event: str, correlation_id: str, status: str, customer_id: int | None = None, **details: object) -> None: ...
