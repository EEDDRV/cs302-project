"""Initialize the local SQLite file with the team's unchanged logical schema."""
import sqlite3
from config import get_config
from frameworks_and_drivers.sqlite_schema import SCHEMA


def main():
    """Create the local SQLite database and eleven tables if absent."""
    from pathlib import Path
    path = Path(get_config()["DB_PATH"]).expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as database:
        database.execute("PRAGMA foreign_keys = ON")
        database.executescript(SCHEMA)
    print(f"SQLite database ready: {path}")


if __name__ == "__main__":
    main()
