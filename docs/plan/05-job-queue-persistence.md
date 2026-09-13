# Job Queue Persistence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** A SQLite-backed job queue that survives app restarts, tracks each download+convert job's status, and supports retry.

**Architecture:** A single `jobs` table. `queue_db.py` exposes plain functions (not a class) taking a `sqlite3.Connection`, so tests can use an in-memory DB (`sqlite3.connect(":memory:")`) and the real app uses a file DB at `%APPDATA%/AudioForge/audioforge.db`.

**Tech Stack:** stdlib `sqlite3`.

**Spec:** [00-overview.md](00-overview.md) §5.4, [ORIGINAL_BRIEF.md](ORIGINAL_BRIEF.md) §5.4

## Global Constraints

- Job statuses: `queued`, `downloading`, `converting`, `tagging`, `done`, `failed`.
- Every job row stores the URL, chosen `ConversionOptions` (as JSON), project name, output path once known, status, error message (nullable), retry count, created_at/updated_at.
- No ORM — plain SQL via `sqlite3`, parameterized queries only (never string-format SQL).

---

### Task 1: Schema + connection helper

**Files:**
- Create: `src/audioforge/core/queue_db.py`
- Test: `tests/core/test_queue_db.py`

**Interfaces:**
- Produces: `connect(db_path: str) -> sqlite3.Connection`, `init_schema(conn) -> None` — consumed by every other function in this file and by `app.py` at startup.

- [ ] **Step 1: Write the failing test**

```python
# tests/core/test_queue_db.py
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
```

- [ ] **Step 2: Run test, verify fails** — `ModuleNotFoundError`

- [ ] **Step 3: Implement**

```python
# src/audioforge/core/queue_db.py
"""SQLite-backed job queue."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone

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
```

- [ ] **Step 4: Run test, verify passes** — 2 passed

- [ ] **Step 5: Commit** — `git add src/audioforge/core/queue_db.py tests/core/test_queue_db.py && git commit -m "feat: add job queue schema and connection helper"`

---

### Task 2: `enqueue`, `get_job`, `list_jobs`, `update_status`

**Files:**
- Modify: `src/audioforge/core/queue_db.py`
- Test: `tests/core/test_queue_db.py` (append)

**Interfaces:**
- Consumes: `ConversionOptions` (sub-plan 2) for JSON serialization via `dataclasses.asdict`.
- Produces: `enqueue(conn, url, project_name, options: ConversionOptions) -> int` (job id), `get_job(conn, job_id) -> dict | None`, `list_jobs(conn, status: str | None = None) -> list[dict]`, `update_status(conn, job_id, status, *, output_path=None, error_message=None) -> None` — consumed by `download_worker.py` and the UI's queue view (sub-plan 6).

- [ ] **Step 1: Write the failing test**

```python
# append to tests/core/test_queue_db.py
import pytest
import sqlite3

from audioforge.core.models import ConversionOptions
from audioforge.core.queue_db import connect, enqueue, get_job, list_jobs, update_status


@pytest.fixture
def conn():
    return connect(":memory:")


def test_enqueue_and_get_job(conn):
    opts = ConversionOptions(format="flac", sample_rate=44100, bit_depth=16)
    job_id = enqueue(conn, "https://youtube.com/watch?v=x", "ClientA", opts)

    job = get_job(conn, job_id)

    assert job["url"] == "https://youtube.com/watch?v=x"
    assert job["status"] == "queued"
    assert job["project_name"] == "ClientA"


def test_list_jobs_filters_by_status(conn):
    opts = ConversionOptions(format="mp3", sample_rate=44100, bit_depth=None)
    id1 = enqueue(conn, "url1", "P", opts)
    enqueue(conn, "url2", "P", opts)
    update_status(conn, id1, "done", output_path="/out/1.mp3")

    done_jobs = list_jobs(conn, status="done")
    queued_jobs = list_jobs(conn, status="queued")

    assert len(done_jobs) == 1
    assert done_jobs[0]["output_path"] == "/out/1.mp3"
    assert len(queued_jobs) == 1


def test_update_status_rejects_invalid_status(conn):
    opts = ConversionOptions(format="mp3", sample_rate=44100, bit_depth=None)
    job_id = enqueue(conn, "url", "P", opts)
    with pytest.raises(ValueError):
        update_status(conn, job_id, "bogus")
```

- [ ] **Step 2: Run test, verify fails** — `ImportError`

- [ ] **Step 3: Implement**

```python
# append to src/audioforge/core/queue_db.py
from dataclasses import asdict

from audioforge.core.models import ConversionOptions


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
```

- [ ] **Step 4: Run test, verify passes** — 3 passed (5 total in file)

- [ ] **Step 5: Commit** — `git commit -am "feat: add job CRUD operations to queue_db"`

---

### Task 3: Retry logic

**Files:**
- Modify: `src/audioforge/core/queue_db.py`
- Test: `tests/core/test_queue_db.py` (append)

**Interfaces:**
- Produces: `retry_job(conn, job_id) -> None` — resets a `failed` job back to `queued` and increments `retry_count`; consumed by the UI's "Retry" button (sub-plan 6).

- [ ] **Step 1: Write the failing test**

```python
# append to tests/core/test_queue_db.py
from audioforge.core.queue_db import retry_job


def test_retry_job_resets_status_and_increments_count(conn):
    opts = ConversionOptions(format="mp3", sample_rate=44100, bit_depth=None)
    job_id = enqueue(conn, "url", "P", opts)
    update_status(conn, job_id, "failed", error_message="network error")

    retry_job(conn, job_id)

    job = get_job(conn, job_id)
    assert job["status"] == "queued"
    assert job["retry_count"] == 1
    assert job["error_message"] is None


def test_retry_job_raises_if_not_failed(conn):
    opts = ConversionOptions(format="mp3", sample_rate=44100, bit_depth=None)
    job_id = enqueue(conn, "url", "P", opts)  # still queued
    with pytest.raises(ValueError):
        retry_job(conn, job_id)
```

- [ ] **Step 2: Run test, verify fails** — `ImportError`

- [ ] **Step 3: Implement**

```python
# append to src/audioforge/core/queue_db.py
def retry_job(conn: sqlite3.Connection, job_id: int) -> None:
    job = get_job(conn, job_id)
    if job is None:
        raise ValueError(f"No job with id {job_id}")
    if job["status"] != "failed":
        raise ValueError(f"Job {job_id} is not failed (status={job['status']!r}); cannot retry")
    conn.execute(
        """UPDATE jobs SET status = 'queued', error_message = NULL,
           retry_count = retry_count + 1, updated_at = ? WHERE id = ?""",
        (_now(), job_id),
    )
    conn.commit()
```

- [ ] **Step 4: Run test, verify passes** — 2 passed (7 total in file)

- [ ] **Step 5: Commit** — `git commit -am "feat: add job retry logic"`
