import sqlite3

import pytest

from audioforge.core.models import ConversionOptions
from audioforge.core.queue_db import connect, enqueue, get_job, init_schema, list_jobs, update_status, retry_job


def test_init_schema_creates_jobs_table():
    conn = sqlite3.connect(":memory:")
    init_schema(conn)

    cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='jobs'")
    assert cursor.fetchone() is not None


def test_init_schema_is_idempotent():
    conn = sqlite3.connect(":memory:")
    init_schema(conn)
    init_schema(conn)  # must not raise


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


def test_update_status_raises_for_nonexistent_job(conn):
    with pytest.raises(ValueError):
        update_status(conn, 12345, "done")


def test_retry_job_resets_status_and_increments_count(conn):
    opts = ConversionOptions(format="mp3", sample_rate=44100, bit_depth=None)
    job_id = enqueue(conn, "url", "P", opts)
    update_status(conn, job_id, "done", output_path="/out/1.mp3")
    update_status(conn, job_id, "failed", error_message="network error")

    retry_job(conn, job_id)

    job = get_job(conn, job_id)
    assert job["status"] == "queued"
    assert job["retry_count"] == 1
    assert job["error_message"] is None
    assert job["output_path"] is None


def test_retry_job_raises_if_not_failed(conn):
    opts = ConversionOptions(format="mp3", sample_rate=44100, bit_depth=None)
    job_id = enqueue(conn, "url", "P", opts)  # still queued
    with pytest.raises(ValueError):
        retry_job(conn, job_id)


def test_connect_persists_jobs_across_connections(tmp_path):
    db_path = str(tmp_path / "queue.db")
    opts = ConversionOptions(format="flac", sample_rate=44100, bit_depth=16)

    conn1 = connect(db_path)
    job_id = enqueue(conn1, "https://youtube.com/watch?v=persisted", "ClientA", opts)
    conn1.close()

    conn2 = connect(db_path)
    job = get_job(conn2, job_id)
    conn2.close()

    assert job is not None
    assert job["url"] == "https://youtube.com/watch?v=persisted"
    assert job["status"] == "queued"
    assert job["project_name"] == "ClientA"
