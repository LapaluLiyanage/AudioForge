from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QMessageBox

DISCLAIMER_TEXT = (
    "AudioForge downloads audio from third-party sources such as YouTube.\n\n"
    "Downloading copyrighted content may violate the source platform's Terms of Service. "
    "Use AudioForge only for personal reference, practice, or non-distributed production work. "
    "Do not redistribute or monetize downloaded material you do not have rights to.\n\n"
    "Note: downloaded audio quality can never exceed the source platform's own encoding "
    "(typically ~128-256 kbps). Converting to WAV/FLAC preserves that quality losslessly "
    "from that point forward, but does not improve it.\n\n"
    "By clicking Accept, you agree to use this tool responsibly."
)


def _settings() -> QSettings:
    return QSettings("AudioForge", "AudioForge")


def show_disclaimer_if_needed() -> bool:
    settings = _settings()
    if settings.value("disclaimer_accepted", False, type=bool):
        return True

    box = QMessageBox()
    box.setWindowTitle("AudioForge — Usage Disclaimer")
    box.setText(DISCLAIMER_TEXT)
    box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
    box.setDefaultButton(QMessageBox.StandardButton.No)
    accept_btn = box.button(QMessageBox.StandardButton.Yes)
    accept_btn.setText("Accept")
    box.button(QMessageBox.StandardButton.No).setText("Decline && Quit")

    accepted = box.exec() == QMessageBox.StandardButton.Yes
    if accepted:
        settings.setValue("disclaimer_accepted", True)
    return accepted
