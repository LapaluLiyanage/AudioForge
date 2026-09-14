from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QMessageBox

from audioforge.ui.disclaimer_dialog import show_disclaimer_if_needed


def test_disclaimer_skipped_if_already_accepted(qtbot, monkeypatch):
    settings = QSettings("AudioForge", "AudioForgeTest")
    settings.setValue("disclaimer_accepted", True)
    monkeypatch.setattr(
        "audioforge.ui.disclaimer_dialog._settings", lambda: settings
    )

    assert show_disclaimer_if_needed() is True


def test_disclaimer_accept_persists_setting_and_returns_true(qtbot, monkeypatch):
    settings = QSettings("AudioForge", "AudioForgeTestAccept")
    settings.remove("disclaimer_accepted")
    monkeypatch.setattr(
        "audioforge.ui.disclaimer_dialog._settings", lambda: settings
    )
    monkeypatch.setattr(QMessageBox, "exec", lambda self: QMessageBox.StandardButton.Yes)

    result = show_disclaimer_if_needed()

    assert result is True
    assert settings.value("disclaimer_accepted", False, type=bool) is True


def test_disclaimer_decline_does_not_persist_and_returns_false(qtbot, monkeypatch):
    settings = QSettings("AudioForge", "AudioForgeTestDecline")
    settings.remove("disclaimer_accepted")
    monkeypatch.setattr(
        "audioforge.ui.disclaimer_dialog._settings", lambda: settings
    )
    monkeypatch.setattr(QMessageBox, "exec", lambda self: QMessageBox.StandardButton.No)

    result = show_disclaimer_if_needed()

    assert result is False
    assert settings.value("disclaimer_accepted", False, type=bool) is False
