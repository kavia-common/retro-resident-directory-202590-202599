from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from typing import Generator

from src.api.utils.errors import APIError


def _get_db_path() -> str:
    # Environment variable is provided by the database container orchestration.
    db_path = os.getenv("SQLITE_DB")
    if not db_path:
        raise APIError(
            status_code=500,
            code="db_not_configured",
            message="Database not configured (missing SQLITE_DB env var).",
        )
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
