from PySide6.QtCore import QSettings

from audioforge.ui.disclaimer_dialog import show_disclaimer_if_needed


def test_disclaimer_skipped_if_already_accepted(qtbot, monkeypatch):
    settings = QSettings("AudioForge", "AudioForgeTest")
    settings.setValue("disclaimer_accepted", True)
    monkeypatch.setattr(
        "audioforge.ui.disclaimer_dialog._settings", lambda: settings
    )

    assert show_disclaimer_if_needed() is True
