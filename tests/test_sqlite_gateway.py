"""Integration checks for the embedded SQLite persistence adapter."""
import sqlite3
from datetime import datetime, timedelta, timezone

import pytest

from entities.models import ApplicationError
from frameworks_and_drivers.sqlite_gateway import SQLiteGateway, token_digest
from frameworks_and_drivers.sqlite_schema import SCHEMA


@pytest.fixture
def database(tmp_path):
    path = tmp_path / "test.sqlite3"
    with sqlite3.connect(path) as connection:
        connection.execute("PRAGMA foreign_keys=ON")
        connection.executescript(SCHEMA)
        customer_id = connection.execute(
            "INSERT INTO Customer (OrganizationName) VALUES ('Sample')"
        ).lastrowid
        connection.execute(
            """INSERT INTO API_Key (BearerTokenHash,CustomerID,MonthlyQuota,RateLimitPerMin)
               VALUES (?,?,2,2)""", (token_digest("token"), customer_id)
        )
        connection.execute("INSERT INTO CaptchaType (TypeCode,TypeName) VALUES ('image','Image')")
        model_id = connection.execute(
            """INSERT INTO AI_Model (ModelName,Version,ArtifactLocation)
               VALUES ('image','v1','local')"""
        ).lastrowid
        connection.execute(
            """INSERT INTO SolverAdapter (AdapterName,TypeCode,Model_ID)
               VALUES ('image','image',?)""", (model_id,)
        )
    return SQLiteGateway({"DB_PATH": str(path)}), path


def test_unmodified_logical_schema_has_eleven_tables(database):
    _, path = database
    with sqlite3.connect(path) as connection:
        tables = {row[0] for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        )}
    assert len(tables) == 11
    assert {"Customer", "API_Key", "SolvingRequest", "SystemAuditLog", "Users", "Role", "UserRole"} <= tables


def test_token_and_monthly_quota(database):
    gateway, path = database
    assert gateway.identify("invalid") is None
    identity = gateway.identify("token")
    assert identity is not None
    adapter = gateway.available_adapter("image")
    assert adapter is not None
    for _ in range(2):
        request_id = gateway.reserve(identity, "image", adapter, "test-correlation")
        gateway.complete(request_id, "SUCCESS", "123", 8, None)
    with pytest.raises(ApplicationError) as error:
        gateway.reserve(identity, "image", adapter, "test-correlation")
    assert error.value.code == "MONTHLY_QUOTA"
    with sqlite3.connect(path) as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM SolvingRequest WHERE CaptchaContentPayload='[REDACTED]'"
        ).fetchone()[0] == 2


def test_expired_key_rejected(database):
    gateway, path = database
    expired = (datetime.now(timezone.utc) - timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")
    with sqlite3.connect(path) as connection:
        connection.execute("UPDATE API_Key SET ExpiresAt=?", (expired,))
    assert gateway.identify("token") is None


def test_model_approval_requires_real_database_evidence(database):
    gateway, path = database
    assert gateway.approved_by(1) is None
    with sqlite3.connect(path) as connection:
        connection.execute("INSERT INTO Users (UserName,Email,PasswordHash) VALUES ('reviewer','reviewer@example.com','placeholder')")
        reviewer_id = connection.execute("SELECT UserID FROM Users WHERE UserName='reviewer'").fetchone()[0]
        connection.execute("INSERT INTO Users (UserName,Email,PasswordHash) VALUES ('admin','admin@example.com','placeholder')")
        admin_id = connection.execute("SELECT UserID FROM Users WHERE UserName='admin'").fetchone()[0]
    gateway.approve_model(1, reviewer_id)
    assert gateway.approved_by(1) == reviewer_id
    gateway.activate_model(1, admin_id)
    assert gateway.approved_by(1) is None
    with sqlite3.connect(path) as connection:
        assert connection.execute("SELECT IsActive FROM AI_Model WHERE Model_ID=1").fetchone()[0] == 1
