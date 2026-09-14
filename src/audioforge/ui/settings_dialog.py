"""Settings dialog for AudioForge.

Reads/writes persistent QSettings keys (output_base_dir, default_format,
default_project_name) and exposes an "Update yt-dlp engine" button. The
update runs `downloader.update_ytdlp()` (which shells out to pip) on a
background QThread (EngineUpdateWorker below) so the UI thread never blocks
waiting on pip -- mirroring the DownloadWorker/DownloadTab pattern used in
download_tab.py (worker kept alive via self._update_worker, same reasoning
as DownloadTab._workers).
"""
from __future__ import annotations

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)

from audioforge.core import downloader

FORMAT_CHOICES = ["wav", "flac", "mp3", "m4a", "opus"]


class EngineUpdateWorker(QThread):
    """Runs downloader.update_ytdlp() off the UI thread."""

    finished = Signal(bool, str)

    def run(self) -> None:
        try:
            version_info = downloader.update_ytdlp()
            self.finished.emit(True, version_info)
        except Exception as exc:
            self.finished.emit(False, str(exc))


class SettingsDialog(QDialog):
    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.settings = settings
        # Keep a strong reference to any running EngineUpdateWorker so it
        # isn't garbage-collected mid-run (same reasoning as
        # DownloadTab._workers in download_tab.py).
        self._update_worker: EngineUpdateWorker | None = None
        self.setWindowTitle("Settings")

        self.output_dir_input = QLineEdit(settings.value("output_base_dir", ""))
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self._browse)

        self.default_format_combo = QComboBox()
        self.default_format_combo.addItems(FORMAT_CHOICES)
        current_format = settings.value("default_format", FORMAT_CHOICES[0])
        if current_format in FORMAT_CHOICES:
            self.default_format_combo.setCurrentText(current_format)

        self.default_project_name_input = QLineEdit(settings.value("default_project_name", ""))

        self.update_engine_btn = QPushButton("Update yt-dlp engine")
        self.update_engine_btn.clicked.connect(self._on_update_engine_clicked)
        self.update_status_label = QLabel("")

        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self._on_save_clicked)

        dir_row = QHBoxLayout()
        dir_row.addWidget(self.output_dir_input)
        dir_row.addWidget(browse_btn)

        engine_row = QHBoxLayout()
        engine_row.addWidget(self.update_engine_btn)
        engine_row.addWidget(self.update_status_label)

        layout = QVBoxLayout(self)
        layout.addLayout(dir_row)
        layout.addWidget(self.default_format_combo)
        layout.addWidget(self.default_project_name_input)
        layout.addLayout(engine_row)
        layout.addWidget(save_btn)

    def _browse(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Choose output folder")
        if path:
            self.output_dir_input.setText(path)

    def save(self) -> None:
        self.settings.setValue("output_base_dir", self.output_dir_input.text())
        self.settings.setValue("default_format", self.default_format_combo.currentText())
        self.settings.setValue("default_project_name", self.default_project_name_input.text())

    def _on_save_clicked(self) -> None:
        self.save()
        self.accept()

    def _on_update_engine_clicked(self) -> None:
        self.update_status_label.setText("Updating...")
        worker = EngineUpdateWorker()
        worker.finished.connect(self._on_update_finished)
        self._update_worker = worker
        worker.start()

    def _on_update_finished(self, success: bool, message: str) -> None:
        if success:
            self.update_status_label.setText(f"yt-dlp updated ({message.strip()})")
        else:
            self.update_status_label.setText(f"Update failed: {message}")
