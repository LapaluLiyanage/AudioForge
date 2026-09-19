import os
from unittest.mock import MagicMock, patch

from audioforge.ui.converter_tab import ConverterTab
from audioforge.ui.queue_grid import QueueGrid


def _make_tab(qtbot):
    grid = QueueGrid()
    qtbot.addWidget(grid)
    tab = ConverterTab(queue_grid=grid)
    qtbot.addWidget(tab)
    return tab, grid


def test_add_files_populates_queue_grid(qtbot):
    tab, grid = _make_tab(qtbot)

    tab.add_files(["/music/track1.wav", "/music/track2.mp3"])

    assert len(grid._order) == 2
    assert grid._fields["cv:0"]["title"] == "track1.wav"


def test_convert_all_disabled_when_no_files(qtbot):
    tab, _grid = _make_tab(qtbot)
    assert not tab.convert_all_btn.isEnabled()

    tab.add_files(["/music/track1.wav"])
    assert tab.convert_all_btn.isEnabled()


@patch("audioforge.ui.converter_tab.QMessageBox.warning")
def test_add_files_rejects_non_audio_with_visible_feedback(mock_warning, qtbot):
    tab, grid = _make_tab(qtbot)

    tab.add_files(["/music/track1.wav", "/docs/notes.txt"])

    assert len(grid._order) == 1
    assert grid._fields["cv:0"]["title"] == "track1.wav"
    assert "/docs/notes.txt" not in tab._input_paths
    mock_warning.assert_called_once()
    warning_args = mock_warning.call_args[0]
    assert "notes.txt" in warning_args[2]


@patch("audioforge.ui.converter_tab.ConvertWorker")
def test_convert_all_writes_next_to_source_when_output_dir_empty(mock_worker_cls, qtbot):
    mock_worker_cls.return_value = MagicMock()
    tab, _grid = _make_tab(qtbot)
    tab.add_files(["/music/track1.wav"])

    tab._convert_all()

    _, args, kwargs = mock_worker_cls.mock_calls[0]
    output_path = args[2]
    assert output_path == "/music/track1_converted.wav"


@patch("audioforge.ui.converter_tab.ConvertWorker")
def test_convert_all_writes_into_chosen_output_dir(mock_worker_cls, qtbot):
    mock_worker_cls.return_value = MagicMock()
    tab, _grid = _make_tab(qtbot)
    tab.add_files(["/music/track1.wav"])
    tab.output_dir = "/exports"

    tab._convert_all()

    _, args, kwargs = mock_worker_cls.mock_calls[0]
    output_path = args[2]
    assert output_path == os.path.join("/exports", "track1_converted.wav")


@patch("audioforge.ui.converter_tab.ConvertWorker")
def test_convert_all_uses_selected_format_and_quality(mock_worker_cls, qtbot):
    mock_worker_cls.return_value = MagicMock()
    tab, _grid = _make_tab(qtbot)
    tab.add_files(["/music/track1.wav"])
    tab.format_row.set_value("flac")
    tab.quality_row.set_value((48000, 24))

    tab._convert_all()

    _, args, kwargs = mock_worker_cls.mock_calls[0]
    options = args[3]
    assert options.format == "flac"
    assert options.sample_rate == 48000
    assert options.bit_depth == 24


@patch("audioforge.ui.converter_tab.ConvertWorker")
def test_convert_all_disables_button_and_re_enables_after_batch(mock_worker_cls, qtbot):
    mock_worker_cls.return_value = MagicMock()
    tab, _grid = _make_tab(qtbot)
    tab.add_files(["/music/track1.wav", "/music/track2.wav"])

    tab._convert_all()
    assert not tab.convert_all_btn.isEnabled()

    tab._on_finished_one(0, "/music/track1_converted.wav")
    assert not tab.convert_all_btn.isEnabled()

    tab._on_failed_one(1, "boom")
    assert tab.convert_all_btn.isEnabled()


@patch("audioforge.ui.converter_tab.ConvertWorker")
def test_convert_all_skips_rows_already_done(mock_worker_cls, qtbot):
    mock_worker_cls.return_value = MagicMock()
    tab, _grid = _make_tab(qtbot)
    tab.add_files(["/music/track1.wav", "/music/track2.wav"])

    tab._convert_all()
    tab._on_finished_one(0, "/music/track1_converted.wav")
    tab._on_finished_one(1, "/music/track2_converted.wav")

    mock_worker_cls.reset_mock()
    tab._convert_all()

    mock_worker_cls.assert_not_called()
    assert tab.convert_all_btn.isEnabled()


def test_on_finished_one_updates_status_and_prunes_worker(qtbot):
    tab, grid = _make_tab(qtbot)
    tab.add_files(["/music/track1.wav"])
    tab._workers[0] = MagicMock()

    tab._on_finished_one(0, "/music/track1_converted.wav")

    assert grid._fields["cv:0"]["status"] == "done"
    assert 0 not in tab._workers


def test_on_failed_one_updates_status_and_prunes_worker(qtbot):
    tab, grid = _make_tab(qtbot)
    tab.add_files(["/music/track1.wav"])
    tab._workers[0] = MagicMock()

    tab._on_failed_one(0, "ffmpeg exploded")

    assert grid._fields["cv:0"]["status"] == "failed"
    assert grid._fields["cv:0"]["error"] == "ffmpeg exploded"
    assert 0 not in tab._workers


def test_drop_event_accepts_proposed_action(qtbot):
    from unittest.mock import MagicMock as _MM

    tab, _grid = _make_tab(qtbot)
    event = _MM()
    event.mimeData.return_value.urls.return_value = []

    tab.dropEvent(event)

    event.acceptProposedAction.assert_called_once()


def test_shutdown_waits_on_running_workers(qtbot):
    tab, _grid = _make_tab(qtbot)
    running_worker = MagicMock()
    running_worker.isRunning.return_value = True
    idle_worker = MagicMock()
    idle_worker.isRunning.return_value = False
    tab._workers = {0: running_worker, 1: idle_worker}

    tab.shutdown()

    running_worker.wait.assert_called_once_with(3000)
    idle_worker.wait.assert_not_called()
