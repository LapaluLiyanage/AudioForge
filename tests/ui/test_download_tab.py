from unittest.mock import MagicMock, patch

from PySide6.QtCore import QSettings

from audioforge.core import queue_db
from audioforge.ui.download_tab import DownloadTab
from audioforge.ui.queue_grid import QueueGrid


def _make_tab_with_db(tmp_path, qtbot):
    conn = queue_db.connect(str(tmp_path / "queue.db"))
    grid = QueueGrid()
    qtbot.addWidget(grid)
    tab = DownloadTab(db_conn=conn, queue_grid=grid)
    qtbot.addWidget(tab)
    return tab, conn, grid


def test_download_disabled_until_url_entered(qtbot):
    grid = QueueGrid()
    qtbot.addWidget(grid)
    tab = DownloadTab(db_conn=None, queue_grid=grid)
    qtbot.addWidget(tab)

    assert not tab.download_btn.isEnabled()

    qtbot.keyClicks(tab.url_input, "https://youtube.com/watch?v=abc")

    assert tab.download_btn.isEnabled()


def test_bit_depth_dropped_for_lossy_formats(qtbot):
    grid = QueueGrid()
    qtbot.addWidget(grid)
    tab = DownloadTab(db_conn=None, queue_grid=grid)
    qtbot.addWidget(tab)

    tab.format_row.set_value("mp3")
    assert tab._current_options().bit_depth is None

    tab.format_row.set_value("flac")
    assert tab._current_options().bit_depth is not None


@patch("audioforge.ui.download_tab.DownloadWorker")
def test_add_to_queue_enqueues_job_and_starts_worker(mock_worker_cls, tmp_path, qtbot):
    mock_worker = MagicMock()
    mock_worker_cls.return_value = mock_worker

    tab, conn, grid = _make_tab_with_db(tmp_path, qtbot)
    qtbot.keyClicks(tab.url_input, "https://youtube.com/watch?v=abc")

    tab._on_add_to_queue()

    jobs = queue_db.list_jobs(conn)
    assert len(jobs) == 1
    assert jobs[0]["status"] == "queued"
    assert jobs[0]["url"] == "https://youtube.com/watch?v=abc"

    job_id = jobs[0]["id"]
    mock_worker_cls.assert_called_once()
    _, kwargs = mock_worker_cls.call_args
    assert kwargs["job_id"] == job_id
    assert kwargs["url"] == "https://youtube.com/watch?v=abc"

    mock_worker.start.assert_called_once()
    assert tab._workers[job_id] is mock_worker
    assert len(grid._order) == 1


@patch("audioforge.ui.download_tab.DownloadWorker")
def test_add_to_queue_uses_settings_project_name_and_output_dir(mock_worker_cls, tmp_path, qtbot):
    mock_worker = MagicMock()
    mock_worker_cls.return_value = mock_worker

    settings = QSettings("AudioForge", "AudioForge")
    settings.setValue("default_project_name", "MyProject")
    settings.setValue("output_base_dir", str(tmp_path / "custom_out"))
    try:
        tab, conn, grid = _make_tab_with_db(tmp_path, qtbot)
        qtbot.keyClicks(tab.url_input, "https://youtube.com/watch?v=abc")

        tab._on_add_to_queue()

        jobs = queue_db.list_jobs(conn)
        assert jobs[0]["project_name"] == "MyProject"
        _, kwargs = mock_worker_cls.call_args
        assert kwargs["project_name"] == "MyProject"
        assert kwargs["base_output_dir"] == str(tmp_path / "custom_out")
    finally:
        settings.remove("default_project_name")
        settings.remove("output_base_dir")


@patch("audioforge.ui.download_tab.DownloadWorker")
def test_status_changed_updates_queue_db_and_card(mock_worker_cls, tmp_path, qtbot):
    mock_worker_cls.return_value = MagicMock()
    tab, conn, grid = _make_tab_with_db(tmp_path, qtbot)
    qtbot.keyClicks(tab.url_input, "https://youtube.com/watch?v=abc")
    tab._on_add_to_queue()
    job_id = queue_db.list_jobs(conn)[0]["id"]

    tab._on_worker_status_changed(job_id, "converting")

    assert queue_db.get_job(conn, job_id)["status"] == "converting"
    key = tab._job_keys[job_id]
    assert grid._fields[key]["status"] == "converting"


@patch("audioforge.ui.download_tab.DownloadWorker")
def test_worker_finished_persists_output_path(mock_worker_cls, tmp_path, qtbot):
    mock_worker_cls.return_value = MagicMock()
    tab, conn, grid = _make_tab_with_db(tmp_path, qtbot)
    qtbot.keyClicks(tab.url_input, "https://youtube.com/watch?v=abc")
    tab._on_add_to_queue()
    job_id = queue_db.list_jobs(conn)[0]["id"]

    assert job_id in tab._workers

    tab._on_worker_finished(job_id, "/out/P/Track.flac")

    job = queue_db.get_job(conn, job_id)
    assert job["output_path"] == "/out/P/Track.flac"
    # _workers must be pruned on completion so it doesn't grow unbounded for
    # the lifetime of a long session.
    assert job_id not in tab._workers


@patch("audioforge.ui.download_tab.DownloadWorker")
def test_worker_failed_updates_queue_db_and_card(mock_worker_cls, tmp_path, qtbot):
    mock_worker_cls.return_value = MagicMock()
    tab, conn, grid = _make_tab_with_db(tmp_path, qtbot)
    qtbot.keyClicks(tab.url_input, "https://youtube.com/watch?v=abc")
    tab._on_add_to_queue()
    job_id = queue_db.list_jobs(conn)[0]["id"]

    assert job_id in tab._workers

    tab._on_worker_failed(job_id, "boom")

    job = queue_db.get_job(conn, job_id)
    assert job["status"] == "failed"
    assert job["error_message"] == "boom"
    key = tab._job_keys[job_id]
    assert grid._fields[key]["status"] == "failed"
    # _workers must be pruned on completion (failure counts as completion)
    # so it doesn't grow unbounded for the lifetime of a long session.
    assert job_id not in tab._workers
