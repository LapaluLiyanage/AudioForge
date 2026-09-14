from unittest.mock import MagicMock, patch

from audioforge.ui.converter_tab import ConverterTab
from audioforge.ui.main_window import MainWindow


def test_main_window_has_correct_title(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)
    assert window.windowTitle() == "AudioForge"


def test_main_window_has_convert_tab(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)

    assert window.tabs.tabText(1) == "Convert"
    assert isinstance(window.converter_tab, ConverterTab)


@patch("audioforge.ui.main_window.SettingsDialog")
def test_settings_action_opens_settings_dialog(mock_dialog_cls, qtbot):
    mock_dialog = MagicMock()
    mock_dialog_cls.return_value = mock_dialog
    window = MainWindow()
    qtbot.addWidget(window)

    window._open_settings_dialog()

    mock_dialog_cls.assert_called_once()
    mock_dialog.exec.assert_called_once()


def test_close_event_shuts_down_workers_and_closes_db(qtbot):
    import sqlite3

    window = MainWindow()
    qtbot.addWidget(window)
    window.download_tab.shutdown = MagicMock()
    window.converter_tab.shutdown = MagicMock()

    window.close()

    window.download_tab.shutdown.assert_called_once()
    window.converter_tab.shutdown.assert_called_once()
    try:
        window.db_conn.execute("SELECT 1")
        closed = False
    except sqlite3.ProgrammingError:
        closed = True
    assert closed
