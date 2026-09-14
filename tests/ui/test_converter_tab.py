import os
from unittest.mock import MagicMock, patch

from audioforge.ui.converter_tab import ConverterTab


def test_add_files_populates_table(qtbot):
    tab = ConverterTab()
    qtbot.addWidget(tab)

    tab.add_files(["/music/track1.wav", "/music/track2.mp3"])

    assert tab.file_table.rowCount() == 2
    assert tab.file_table.item(0, 0).text() == "track1.wav"


def test_convert_all_disabled_when_no_files(qtbot):
    tab = ConverterTab()
    qtbot.addWidget(tab)
    assert not tab.convert_all_btn.isEnabled()

    tab.add_files(["/music/track1.wav"])
    assert tab.convert_all_btn.isEnabled()


@patch("audioforge.ui.converter_tab.QMessageBox.warning")
def test_add_files_rejects_non_audio_with_visible_feedback(mock_warning, qtbot):
    tab = ConverterTab()
    qtbot.addWidget(tab)

    tab.add_files(["/music/track1.wav", "/docs/notes.txt"])

    assert tab.file_table.rowCount() == 1
    assert tab.file_table.item(0, 0).text() == "track1.wav"
    assert "/docs/notes.txt" not in tab._input_paths
    mock_warning.assert_called_once()
    warning_args = mock_warning.call_args[0]
    assert "notes.txt" in warning_args[2]


@patch("audioforge.ui.converter_tab.ConvertWorker")
def test_convert_all_writes_next_to_source_when_output_dir_empty(mock_worker_cls, qtbot):
    mock_worker_cls.return_value = MagicMock()
    tab = ConverterTab()
    qtbot.addWidget(tab)
    tab.add_files(["/music/track1.wav"])

    tab._convert_all()

    _, args, kwargs = mock_worker_cls.mock_calls[0]
    output_path = args[2]
    assert output_path == "/music/track1_converted.wav"


@patch("audioforge.ui.converter_tab.ConvertWorker")
def test_convert_all_writes_into_chosen_output_dir(mock_worker_cls, qtbot):
    mock_worker_cls.return_value = MagicMock()
    tab = ConverterTab()
    qtbot.addWidget(tab)
    tab.add_files(["/music/track1.wav"])
    tab.output_dir_input.setText("/exports")

    tab._convert_all()

    _, args, kwargs = mock_worker_cls.mock_calls[0]
    output_path = args[2]
    assert output_path == os.path.join("/exports", "track1_converted.wav")
