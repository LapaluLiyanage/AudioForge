import sqlite3

from audioforge.core.queue_db import init_schema


def test_init_schema_creates_jobs_table():
    conn = sqlite3.connect(":memory:")
    init_schema(conn)

    cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='jobs'")
    assert cursor.fetchone() is not None


def test_init_schema_is_idempotent():
    conn = sqlite3.connect(":memory:")
    init_schema(conn)
    init_schema(conn)  # must not raise
