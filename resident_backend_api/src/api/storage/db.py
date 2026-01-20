from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from typing import Generator




def _get_db_path() -> str:
    """
    Resolve the SQLite DB file path.

    Primary source:
      - SQLITE_DB env var (provided by the database container orchestration)

    Fallback:
      - Use the known database workspace file if SQLITE_DB is missing. This
        improves local/dev robustness during multi-container integration.

    Notes:
      - If SQLITE_DB is a relative path, resolve it relative to the current
        working directory.
    """
    db_path = os.getenv("SQLITE_DB")

    # Fallback path discovered from database container's db_connection.txt
    fallback_path = "/home/kavia/workspace/code-generation/retro-resident-directory-202590-202600/database/myapp.db"

    if not db_path or db_path.strip() == "":
        db_path = fallback_path

    db_path = db_path.strip()

    if not os.path.isabs(db_path):
        db_path = os.path.abspath(db_path)

    return db_path


@contextmanager
def get_conn() -> Generator[sqlite3.Connection, None, None]:
    """Context manager for SQLite connections with sensible defaults."""
    conn = sqlite3.connect(_get_db_path())
    try:
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# PUBLIC_INTERFACE
def init_db() -> None:
    """Initialize the SQLite schema required by the application."""
    with get_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS residents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name TEXT NOT NULL,
                unit TEXT,
                phone TEXT,
                email TEXT,
                status TEXT NOT NULL DEFAULT 'active',
                notes TEXT,
                move_in_date TEXT,
                tags_json TEXT NOT NULL DEFAULT '[]',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_residents_full_name ON residents(full_name);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_residents_unit ON residents(unit);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_residents_status ON residents(status);")
