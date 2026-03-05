"""SQLite connection utilities for the refactored routing backend."""

from __future__ import annotations

import sqlite3
from pathlib import Path

DEFAULT_DB_PATH = Path("route_planner/database/db.sqlite")


def get_connection(db_path: str | Path | None = None) -> sqlite3.Connection:
    """Return a SQLite connection configured with Row factory and FK checks."""
    path = Path(db_path) if db_path else DEFAULT_DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn
