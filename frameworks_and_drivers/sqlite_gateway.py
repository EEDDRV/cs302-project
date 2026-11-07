"""Embedded SQLite adapter for the original eleven-table logical database schema."""
import hashlib
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path


from entities.models import ApplicationError, CustomerIdentity


def token_digest(token: str) -> str:
    """Return the SHA-256 digest used for indexed API-key lookup.

    Args:
        token: High-entropy bearer token.

    Returns:
        Hexadecimal digest.
    """
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def utc_now() -> str:
    """Return a UTC timestamp in SQLite-compatible format.

    Returns:
        UTC date and time.
    """
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


class SQLiteGateway:
    """Use one local SQLite file for authentication, usage, and review records."""

    def __init__(self, config: dict):
        self.path = Path(config["DB_PATH"]).expanduser().resolve()
        if not self.path.exists():
            raise RuntimeError(
                f"Database not initialized: {self.path}. Run 'python init_db.py' first."
            )

    @contextmanager
    def _connect(self):
        """Open a transaction-scoped SQLite connection with foreign keys enabled.

        Yields:
            A connection that commits on success and rolls back on failure.
        """
        connection = sqlite3.connect(self.path, timeout=15, isolation_level=None)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 15000")
        try:
            yield connection
        finally:
            connection.close()

    @staticmethod
    def _begin(connection):
        # SQLite BEGIN IMMEDIATE obtains the single writer reservation before
        # quota checks, making concurrent reservations across processes safe.
        connection.execute("BEGIN IMMEDIATE")

    def identify(self, bearer_token: str) -> CustomerIdentity | None:
        if not bearer_token:
            return None
        with self._connect() as db:
            row = db.execute(
                """SELECT k.KeyID, k.CustomerID, k.MonthlyQuota, k.RateLimitPerMin
                   FROM API_Key k JOIN Customer c ON c.CustomerID=k.CustomerID
                   WHERE k.BearerTokenHash=? AND k.IsActive=1
                     AND c.Status='ACTIVE'
                     AND (k.ExpiresAt IS NULL OR k.ExpiresAt>?)""",
                (token_digest(bearer_token), utc_now()),
            ).fetchone()
        return (CustomerIdentity(row["CustomerID"], row["KeyID"], row["MonthlyQuota"],
                                 row["RateLimitPerMin"]) if row else None)

    def available_adapter(self, captcha_type: str) -> int | None:
        with self._connect() as db:
            row = db.execute(
                """SELECT sa.SolverID FROM SolverAdapter sa
                   JOIN CaptchaType ct ON ct.TypeCode=sa.TypeCode
                   JOIN AI_Model m ON m.Model_ID=sa.Model_ID
                   WHERE sa.TypeCode=? AND ct.IsSupported=1
                     AND sa.IsActive=1 AND m.IsActive=1
                   ORDER BY sa.SolverID LIMIT 1""", (captcha_type,),
            ).fetchone()
        return row["SolverID"] if row else None

    def reserve(self, identity: CustomerIdentity, captcha_type: str,
                adapter_id: int, correlation_id: str) -> int:
        now = datetime.now(timezone.utc)
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        minute_start = now - timedelta(seconds=60)
        with self._connect() as db:
            self._begin(db)
            try:
                key = db.execute(
                    "SELECT IsActive, MonthlyQuota, RateLimitPerMin FROM API_Key WHERE KeyID=?",
                    (identity.key_id,),
                ).fetchone()
                if not key or not key["IsActive"]:
                    raise ApplicationError("API key is inactive.", 401, "UNAUTHORIZED")
                count_month = db.execute(
                    "SELECT COUNT(*) FROM SolvingRequest WHERE KeyID=? AND RequestedAt>=?",
                    (identity.key_id, month_start.strftime("%Y-%m-%d %H:%M:%S")),
                ).fetchone()[0]
                count_minute = db.execute(
                    "SELECT COUNT(*) FROM SolvingRequest WHERE KeyID=? AND RequestedAt>=?",
                    (identity.key_id, minute_start.strftime("%Y-%m-%d %H:%M:%S")),
                ).fetchone()[0]
                if count_month >= max(0, key["MonthlyQuota"] or 0):
                    raise ApplicationError("Monthly request quota exceeded.", 429, "MONTHLY_QUOTA")
                if count_minute >= max(0, key["RateLimitPerMin"] or 0):
                    raise ApplicationError("Per-minute request limit exceeded.", 429, "RATE_LIMIT")
                cursor = db.execute(
                    """INSERT INTO SolvingRequest
                       (CaptchaContentPayload, Status, CustomerID, KeyID, DeclaredTypeCode, SolverID,
                        RequestedAt) VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    ("[REDACTED]", "PENDING", identity.customer_id, identity.key_id,
                     captcha_type, adapter_id, utc_now()),
                )
                request_id = cursor.lastrowid
                db.commit()
            except Exception:
                db.rollback()
                raise
        return request_id

    def complete(self, request_id: int, status: str, prediction: str | None,
                 duration_ms: int, error: str | None):
        with self._connect() as db:
            db.execute(
                """UPDATE SolvingRequest SET Status=?, PredictedSolution=?,
                   ProcessingTimeMs=?, ErrorMessage=? WHERE RequestID=?""",
                (status, prediction, duration_ms, error, request_id),
            )

    def insert_event(self, event: str, status: str, data: dict, customer_id: int | None):
        with self._connect() as db:
            db.execute(
                """INSERT INTO SystemAuditLog (EventType, Severity, Details, CustomerID)
                   VALUES (?, ?, ?, ?)""",
                (event[:50], "INFO" if status in ("SUCCESS", "STARTED", "APPROVED", "ACTIVATED")
                 else "WARNING", json.dumps(data), customer_id),
            )

    def authenticate_reviewer(self, username: str, password: str, role: str) -> int | None:
        if not username or not password:
            return None
        with self._connect() as db:
            row = db.execute(
                """SELECT u.UserID, u.PasswordHash FROM Users u
                   JOIN UserRole ur ON ur.UserID=u.UserID
                   JOIN Role r ON r.RoleID=ur.RoleID
                   WHERE u.UserName=? AND u.IsActive=1 AND r.RoleName=?""",
                (username, role),
            ).fetchone()
        if row is None:
            return None
        try:
            import bcrypt
            return (row["UserID"] if bcrypt.checkpw(password.encode("utf-8"),
                                                      row["PasswordHash"].encode("utf-8")) else None)
        except (ValueError, TypeError):
            return None

    def approve_model(self, model_id: int, reviewer_id: int):
        with self._connect() as db:
            self._begin(db)
            try:
                if db.execute("SELECT 1 FROM AI_Model WHERE Model_ID=?", (model_id,)).fetchone() is None:
                    raise ApplicationError("Unknown model ID.", 404, "MODEL_NOT_FOUND")
                db.execute(
                    """INSERT INTO SystemAuditLog (EventType, Severity, Details, UserID)
                       VALUES ('model.approval','INFO',?,?)""",
                    (json.dumps({"model_id": model_id, "reviewer_id": reviewer_id,
                                 "action": "APPROVE"}), reviewer_id),
                )
                db.commit()
            except Exception:
                db.rollback()
                raise

    def approved_by(self, model_id: int) -> int | None:
        with self._connect() as db:
            rows = db.execute(
                """SELECT LogID, UserID, Details FROM SystemAuditLog
                   WHERE EventType='model.approval' ORDER BY LogID DESC"""
            ).fetchall()
        for row in rows:
            try:
                detail = json.loads(row["Details"])
            except (ValueError, TypeError):
                continue
            if detail.get("model_id") == model_id:
                return row["UserID"] if detail.get("action") == "APPROVE" else None
        return None

    def activate_model(self, model_id: int, admin_id: int):
        with self._connect() as db:
            self._begin(db)
            try:
                cursor = db.execute("UPDATE AI_Model SET IsActive=1 WHERE Model_ID=?", (model_id,))
                if cursor.rowcount == 0:
                    raise ApplicationError("Unknown model ID.", 404, "MODEL_NOT_FOUND")
                db.execute(
                    """INSERT INTO SystemAuditLog (EventType, Severity, Details, UserID)
                       VALUES ('model.approval','INFO',?,?)""",
                    (json.dumps({"model_id": model_id, "action": "ACTIVATE",
                                 "admin_id": admin_id}), admin_id),
                )
                db.commit()
            except Exception:
                db.rollback()
                raise
