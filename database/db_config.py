import os
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_DB_PATH = BASE_DIR / "support_coaching.db"


def get_db_path() -> str:
    return os.getenv("SQLITE_DB_PATH", str(DEFAULT_DB_PATH))


def get_connection() -> sqlite3.Connection:
    """Returns a SQLite connection with dictionary-like rows and Foreign Keys ON."""
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db() -> None:
    """Creates all SQL tables from schema.sql and inserts initial seed data."""
    schema_file = BASE_DIR / "schema.sql"
    seed_file = BASE_DIR / "seed.sql"

    with get_connection() as conn:
        if schema_file.exists():
            conn.executescript(schema_file.read_text(encoding="utf-8"))
        if seed_file.exists():
            conn.executescript(seed_file.read_text(encoding="utf-8"))
        conn.commit()