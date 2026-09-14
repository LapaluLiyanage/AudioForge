from unittest.mock import patch

from audioforge.core.models import ConversionOptions
from audioforge.workers.convert_worker import ConvertWorker


@patch("audioforge.workers.convert_worker.convert")
def test_convert_worker_emits_finished_one_on_success(mock_convert, qtbot):
    mock_convert.return_value.output_path = "/out/file.flac"
    opts = ConversionOptions(format="flac", sample_rate=44100, bit_depth=16)
    worker = ConvertWorker(index=0, input_path="/in/file.wav", output_path="/out/file.flac", options=opts)

    with qtbot.waitSignal(worker.finished_one, timeout=2000) as blocker:
        worker.start()
    worker.wait()

    assert blocker.args == [0, "/out/file.flac"]


@patch("audioforge.workers.convert_worker.convert", side_effect=Exception("bad file"))
def test_convert_worker_emits_failed_one_on_error(mock_convert, qtbot):
    opts = ConversionOptions(format="mp3", sample_rate=44100, bit_depth=None)
    worker = ConvertWorker(index=1, input_path="/in/broken", output_path="/out/broken.mp3", options=opts)

    with qtbot.waitSignal(worker.failed_one, timeout=2000) as blocker:
        worker.start()
    worker.wait()

    assert blocker.args == [1, "bad file"]
