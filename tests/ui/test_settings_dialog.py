from unittest.mock import MagicMock, patch

from PySide6.QtCore import QSettings

from audioforge.ui.settings_dialog import SettingsDialog


def test_settings_dialog_loads_and_saves_output_dir(qtbot, tmp_path):
    settings = QSettings("AudioForge", "AudioForgeTestSettings")
    dialog = SettingsDialog(settings=settings)
    qtbot.addWidget(dialog)

    dialog.output_dir_input.setText(str(tmp_path))
    dialog.save()

    assert settings.value("output_base_dir") == str(tmp_path)


def test_settings_dialog_loads_and_saves_default_format(qtbot):
    settings = QSettings("AudioForge", "AudioForgeTestSettings")
    settings.setValue("default_format", "flac")
    dialog = SettingsDialog(settings=settings)
    qtbot.addWidget(dialog)

    assert dialog.default_format_combo.currentText() == "flac"

    dialog.default_format_combo.setCurrentText("mp3")
    dialog.save()

    assert settings.value("default_format") == "mp3"


def test_settings_dialog_loads_and_saves_default_project_name(qtbot):
    settings = QSettings("AudioForge", "AudioForgeTestSettings")
    settings.setValue("default_project_name", "MyProject")
    dialog = SettingsDialog(settings=settings)
    qtbot.addWidget(dialog)

    assert dialog.default_project_name_input.text() == "MyProject"

    dialog.default_project_name_input.setText("OtherProject")
    dialog.save()

    assert settings.value("default_project_name") == "OtherProject"


@patch("audioforge.ui.settings_dialog.EngineUpdateWorker")
def test_update_engine_button_starts_worker_without_blocking(mock_worker_cls, qtbot):
    mock_worker = MagicMock()
    mock_worker_cls.return_value = mock_worker

    settings = QSettings("AudioForge", "AudioForgeTestSettings")
    dialog = SettingsDialog(settings=settings)
    qtbot.addWidget(dialog)

    dialog._on_update_engine_clicked()

    mock_worker_cls.assert_called_once()
    mock_worker.update_finished.connect.assert_called_once()
    mock_worker.start.assert_called_once()
    assert dialog._update_worker is mock_worker


def test_update_engine_finished_shows_feedback_on_success(qtbot):
    settings = QSettings("AudioForge", "AudioForgeTestSettings")
    dialog = SettingsDialog(settings=settings)
    qtbot.addWidget(dialog)

    dialog._on_update_finished(True, "2024.01.01")

    assert "2024.01.01" in dialog.update_status_label.text()


def test_update_engine_finished_shows_feedback_on_failure(qtbot):
    settings = QSettings("AudioForge", "AudioForgeTestSettings")
    dialog = SettingsDialog(settings=settings)
    qtbot.addWidget(dialog)

    dialog._on_update_finished(False, "network error")

    assert "network error" in dialog.update_status_label.text()
