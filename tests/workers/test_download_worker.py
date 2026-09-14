from unittest.mock import patch

from audioforge.core.models import ConversionOptions, TrackMetadata
from audioforge.workers.download_worker import DownloadWorker


@patch("audioforge.workers.download_worker.write_tags")
@patch("audioforge.workers.download_worker.convert")
@patch("audioforge.workers.download_worker.resolve_output_path", return_value="/out/Track.flac")
@patch("audioforge.workers.download_worker.download_audio", return_value="/tmp/raw.webm")
@patch("audioforge.workers.download_worker.probe")
def test_worker_runs_full_pipeline_and_emits_done(
    mock_probe, mock_download, mock_resolve, mock_convert, mock_tag, qtbot
):
    mock_probe.return_value = TrackMetadata(
        id="x", title="Track", uploader="Ch", duration_seconds=10, url="u"
    )
    opts = ConversionOptions(format="flac", sample_rate=44100, bit_depth=16)
    worker = DownloadWorker(job_id=1, url="u", project_name="P", options=opts, base_output_dir="/out")

    statuses = []
    worker.status_changed.connect(lambda job_id, status: statuses.append(status))

    with qtbot.waitSignal(worker.status_changed, timeout=2000):
        worker.start()
    worker.wait()

    assert "downloading" in statuses
    assert "converting" in statuses
    assert "done" in statuses
    mock_convert.assert_called_once()
    mock_tag.assert_called_once()


@patch("audioforge.workers.download_worker.write_tags")
@patch("audioforge.workers.download_worker.convert")
@patch("audioforge.workers.download_worker.resolve_output_path", return_value="/out/Track.flac")
@patch("audioforge.workers.download_worker.download_audio", return_value="/tmp/raw.webm")
@patch("audioforge.workers.download_worker.probe")
def test_worker_emits_job_finished_with_output_path(
    mock_probe, mock_download, mock_resolve, mock_convert, mock_tag, qtbot
):
    mock_probe.return_value = TrackMetadata(
        id="x", title="Track", uploader="Ch", duration_seconds=10, url="u"
    )
    opts = ConversionOptions(format="flac", sample_rate=44100, bit_depth=16)
    worker = DownloadWorker(job_id=7, url="u", project_name="P", options=opts, base_output_dir="/out")

    with qtbot.waitSignal(worker.job_finished, timeout=2000) as blocker:
        worker.start()
    worker.wait()

    assert blocker.args == [7, "/out/Track.flac"]


@patch("audioforge.workers.download_worker.probe")
def test_worker_rejects_playlist_url_with_clear_message(mock_probe, qtbot):
    mock_probe.return_value = [
        TrackMetadata(id="a", title="A", uploader="Ch", duration_seconds=1, url="u1"),
        TrackMetadata(id="b", title="B", uploader="Ch", duration_seconds=1, url="u2"),
    ]
    opts = ConversionOptions(format="mp3", sample_rate=44100, bit_depth=None)
    worker = DownloadWorker(job_id=3, url="playlist-u", project_name="P", options=opts, base_output_dir="/out")

    with qtbot.waitSignal(worker.failed, timeout=2000) as blocker:
        worker.start()
    worker.wait()

    assert blocker.args[0] == 3
    message = blocker.args[1]
    assert "AttributeError" not in message
    assert "playlist" in message.lower()


@patch("audioforge.workers.download_worker.probe", side_effect=Exception("boom"))
def test_worker_emits_failed_on_exception(mock_probe, qtbot):
    from audioforge.core.models import ConversionOptions
    opts = ConversionOptions(format="mp3", sample_rate=44100, bit_depth=None)
    worker = DownloadWorker(job_id=2, url="u", project_name="P", options=opts, base_output_dir="/out")

    with qtbot.waitSignal(worker.failed, timeout=2000) as blocker:
        worker.start()
    worker.wait()

    assert blocker.args[0] == 2
    assert "boom" in blocker.args[1]
