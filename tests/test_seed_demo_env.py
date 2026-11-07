"""Check automatic demo token persistence."""
from pathlib import Path

from dotenv import dotenv_values
from seed_demo import save_demo_token


def test_seed_writes_token_and_preserves_existing_settings(tmp_path: Path):
    env_path = tmp_path / ".env"
    env_path.write_text("HOST=127.0.0.1\nPORT=5001\nDEMO_API_TOKEN=old-token\n")
    save_demo_token("new-demo-token", env_path)
    settings = dotenv_values(env_path)
    assert settings["DEMO_API_TOKEN"] == "new-demo-token"
    assert settings["PORT"] == "5001"
    assert settings["HOST"] == "127.0.0.1"
    save_demo_token("new-demo-token", env_path)
    assert env_path.read_text().count("DEMO_API_TOKEN=") == 1


def test_seed_creates_env_from_example(tmp_path: Path):
    (tmp_path / ".env.example").write_text("PORT=5000\nDEMO_API_TOKEN=\n")
    env_path = tmp_path / ".env"
    save_demo_token("new-demo-token", env_path)
    settings = dotenv_values(env_path)
    assert settings["PORT"] == "5000"
    assert settings["DEMO_API_TOKEN"] == "new-demo-token"
