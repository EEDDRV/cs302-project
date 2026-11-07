"""Observability decorator for the primary use case."""
import time
from entities.models import ApplicationError


class ObservableSolve:
    """Record a redacted outcome around each use-case invocation."""

    def __init__(self, inner, events):
        self.inner = inner
        self.events = events

    def execute(self, command):
        started = time.perf_counter()
        self.events.record("captcha.solve.started", command.correlation_id, "STARTED")
        try:
            return self.inner.execute(command)
        except ApplicationError as exc:
            self.events.record("captcha.solve.rejected", command.correlation_id, exc.code,
                               processing_time_ms=round((time.perf_counter()-started)*1000))
            raise
        except Exception:
            self.events.record("captcha.solve.error", command.correlation_id, "INTERNAL_ERROR")
            raise
