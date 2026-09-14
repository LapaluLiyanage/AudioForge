"""SQLite-backed job queue."""
from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict
from datetime import datetime, timezone

from audioforge.core.models import ConversionOptions

SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    url TEXT NOT NULL,
    project_name TEXT NOT NULL,
    options_json TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'queued',
    output_path TEXT,
    error_message TEXT,
    retry_count INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""

VALID_STATUSES = {"queued", "downloading", "converting", "tagging", "done", "failed"}


def connect(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    init_schema(conn)
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    conn.execute(SCHEMA)
    conn.commit()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def enqueue(conn: sqlite3.Connection, url: str, project_name: str, options: ConversionOptions) -> int:
    now = _now()
    cursor = conn.execute(
        """INSERT INTO jobs (url, project_name, options_json, status, created_at, updated_at)
           VALUES (?, ?, ?, 'queued', ?, ?)""",
        (url, project_name, json.dumps(asdict(options)), now, now),
    )
    conn.commit()
    return cursor.lastrowid


def get_job(conn: sqlite3.Connection, job_id: int) -> dict | None:
    row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
    return dict(row) if row else None


def list_jobs(conn: sqlite3.Connection, status: str | None = None) -> list[dict]:
    if status:
        rows = conn.execute("SELECT * FROM jobs WHERE status = ? ORDER BY id", (status,)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM jobs ORDER BY id").fetchall()
    return [dict(row) for row in rows]


def update_status(
    conn: sqlite3.Connection,
    job_id: int,
    status: str,
    *,
    output_path: str | None = None,
    error_message: str | None = None,
) -> None:
    if status not in VALID_STATUSES:
        raise ValueError(f"Invalid status: {status!r}. Must be one of {sorted(VALID_STATUSES)}")
    conn.execute(
        """UPDATE jobs SET status = ?, output_path = COALESCE(?, output_path),
           error_message = ?, updated_at = ? WHERE id = ?""",
        (status, output_path, error_message, _now(), job_id),
    )
    conn.commit()
