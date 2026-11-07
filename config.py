"""Environment-driven deployment configuration."""
import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


def get_config() -> dict:
    """Read runtime settings with safe local-development defaults."""
    return {
        "HOST": os.getenv("HOST", "127.0.0.1"),
        "PORT": int(os.getenv("PORT", "5000")),
        "DEBUG": os.getenv("DEBUG", "false").lower() == "true",
        "DB_PATH": str((BASE_DIR / os.getenv("DB_PATH", "prompt_platoon.sqlite3")).resolve()),
        "MAX_IMAGE_BYTES": int(os.getenv("MAX_IMAGE_BYTES", str(5 * 1024 * 1024))),
        "MAX_INFERENCE_MS": int(os.getenv("MAX_INFERENCE_MS", "10000")),
        "MAX_CASE_COST_USD": float(os.getenv("MAX_CASE_COST_USD", "0")),
        "ESTIMATED_CASE_COST_USD": float(os.getenv("ESTIMATED_CASE_COST_USD", "0")),
    }
