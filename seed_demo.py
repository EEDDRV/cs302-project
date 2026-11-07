"""Seed sample data in the local SQLite database without modifying its schema."""
import argparse
import getpass
import os
import secrets
from pathlib import Path
from shutil import copyfile

from dotenv import set_key

from config import get_config
from frameworks_and_drivers.sqlite_gateway import SQLiteGateway, token_digest



def save_demo_token(token: str, env_path: Path) -> None:
    """Store the demo token in the project .env without replacing other settings.

    Args:
        token: Plaintext bearer token created or reused for the demo.
        env_path: Destination environment configuration path.

    Returns:
        None.
    """
    if not env_path.exists():
        template = env_path.with_name(".env.example")
        if template.is_file():
            copyfile(template, env_path)
        else:
            env_path.touch(mode=0o600)
    success, _, _ = set_key(str(env_path), "DEMO_API_TOKEN", token, quote_mode="never")
    if not success:
        raise OSError(f"Unable to save demo token in {env_path}")
    try:
        os.chmod(env_path, 0o600)
    except OSError:
        pass  # Windows may not support POSIX file permissions.


def main():
    """Create a demo customer, API token, image adapter and optional review users."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--review-users", action="store_true", help="Create reviewer and admin accounts")
    args = parser.parse_args()
    token = os.getenv("DEMO_API_TOKEN") or secrets.token_urlsafe(36)
    gateway = SQLiteGateway(get_config())
    with gateway._connect() as db:
        db.execute("BEGIN IMMEDIATE")
        try:
            row = db.execute("SELECT CustomerID FROM Customer WHERE OrganizationName=? LIMIT 1",
                             ("Prototype Demo Customer",)).fetchone()
            if row:
                customer_id = row["CustomerID"]
                db.execute("UPDATE Customer SET Status='ACTIVE' WHERE CustomerID=?", (customer_id,))
            else:
                customer_id = db.execute(
                    "INSERT INTO Customer (OrganizationName, Status) VALUES (?, 'ACTIVE')",
                    ("Prototype Demo Customer",),
                ).lastrowid
            db.execute(
                """INSERT INTO API_Key
                   (BearerTokenHash, KeyName, CustomerID, IsActive, MonthlyQuota, RateLimitPerMin)
                   VALUES (?,'M3 Demo',?,1,1000,120)
                   ON CONFLICT(BearerTokenHash) DO UPDATE SET IsActive=1""",
                (token_digest(token), customer_id),
            )
            db.execute(
                """INSERT INTO CaptchaType (TypeCode, TypeName, InputFormat, IsSupported)
                   VALUES ('image','Image CAPTCHA','IMAGE_BYTES',1)
                   ON CONFLICT(TypeCode) DO UPDATE SET IsSupported=1"""
            )
            model = db.execute(
                "SELECT Model_ID FROM AI_Model WHERE ModelName='captcha_model.pt' AND Version='demo-v1' LIMIT 1"
            ).fetchone()
            if model:
                model_id = model["Model_ID"]
            else:
                model_id = db.execute(
                    """INSERT INTO AI_Model (ModelName,Version,Framework,ArtifactLocation,IsActive)
                       VALUES ('captcha_model.pt','demo-v1','PyTorch',?,1)""",
                    ("captcha_solver/adapters/image/captcha_model.pt",),
                ).lastrowid
            adapter = db.execute(
                "SELECT SolverID FROM SolverAdapter WHERE TypeCode='image' AND Model_ID=? LIMIT 1",
                (model_id,),
            ).fetchone()
            if not adapter:
                db.execute(
                    """INSERT INTO SolverAdapter
                       (AdapterName, ProvidesConfidence, IsActive, TypeCode, Model_ID)
                       VALUES ('ImageOCR',0,1,'image',?)""", (model_id,)
                )
            if args.review_users:
                for role_name in ("REVIEWER", "ADMIN"):
                    db.execute(
                        """INSERT INTO Role (RoleName,Description) VALUES (?,?)
                           ON CONFLICT(RoleName) DO NOTHING""",
                        (role_name, f"M3 {role_name.lower()} permission"),
                    )
                for username, role_name in (("m3_reviewer", "REVIEWER"), ("m3_admin", "ADMIN")):
                    user = db.execute("SELECT UserID FROM Users WHERE UserName=?", (username,)).fetchone()
                    if user:
                        user_id = user["UserID"]
                    else:
                        password = getpass.getpass(f"Set password for {username} (12+ characters): ")
                        if len(password) < 12:
                            raise ValueError("Use a demo reviewer password of at least 12 characters")
                        import bcrypt
                        hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
                        user_id = db.execute(
                            """INSERT INTO Users (UserName, Email, PasswordHash, IsActive, CustomerID)
                               VALUES (?, ?, ?, 1, ?)""",
                            (username, f"{username}@example.invalid", hashed, customer_id),
                        ).lastrowid
                    db.execute(
                        """INSERT OR IGNORE INTO UserRole (UserID, RoleID)
                           SELECT ?, RoleID FROM Role WHERE RoleName=?""",
                        (user_id, role_name),
                    )
            db.commit()
        except Exception:
            db.rollback()
            raise
    env_path = Path(__file__).resolve().parent / ".env"
    save_demo_token(token, env_path)
    print("Demo customer, key, model, type, and adapter are ready.")
    print("API bearer token saved to .env as DEMO_API_TOKEN (keep this file private).")
    print("The database stores only the token's SHA-256 hash.")
    print(f"Demo model ID: {model_id}")


if __name__ == "__main__":
    main()
