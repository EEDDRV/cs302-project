"""Redacted structured operational events."""
import json
import logging


class AuditEvents:
    """Write safe JSON-lines and optionally persist to the existing audit table."""

    def __init__(self, logger: logging.Logger, database=None):
        self.logger = logger
        self.database = database

    def record(self, event: str, correlation_id: str, status: str,
               customer_id: int | None = None, **details: object) -> None:
        data = {"event": event, "correlation_id": correlation_id, "status": status,
                "customer_id": customer_id, **details}
        # Events originate from a fixed set of safe fields; no request bodies or tokens.
        self.logger.info(json.dumps(data, separators=(",", ":")))
        if self.database is not None:
            try:
                self.database.insert_event(event, status, data, customer_id)
            except Exception:
                self.logger.exception("Audit persistence failed")
