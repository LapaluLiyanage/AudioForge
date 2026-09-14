import os

from PySide6.QtCore import Qt
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import (
    QComboBox, QFileDialog, QHBoxLayout, QLabel, QPushButton, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget,
)

from audioforge.core.models import ConversionOptions
from audioforge.workers.convert_worker import ConvertWorker

AUDIO_EXTENSIONS = {".wav", ".mp3", ".flac", ".m4a", ".aac", ".ogg", ".opus", ".wma", ".webm"}


class ConverterTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self._input_paths: list[str] = []
        self._workers: list[ConvertWorker] = []

        self.format_combo = QComboBox()
        self.format_combo.addItems(["wav", "flac", "mp3", "m4a", "opus"])
        add_files_btn = QPushButton("Add Files...")
        add_files_btn.clicked.connect(self._browse_files)
        self.convert_all_btn = QPushButton("Convert All")
        self.convert_all_btn.setEnabled(False)
        self.convert_all_btn.clicked.connect(self._convert_all)

        self.file_table = QTableWidget(0, 2)
        self.file_table.setHorizontalHeaderLabels(["File", "Status"])

        drop_hint = QLabel("Drag and drop audio files here, or use Add Files...")
        drop_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)

        top_row = QHBoxLayout()
        top_row.addWidget(add_files_btn)
        top_row.addWidget(self.format_combo)
        top_row.addWidget(self.convert_all_btn)

        layout = QVBoxLayout(self)
        layout.addWidget(drop_hint)
        layout.addLayout(top_row)
        layout.addWidget(self.file_table)

    def add_files(self, paths: list[str]) -> None:
        for path in paths:
            if os.path.splitext(path)[1].lower() not in AUDIO_EXTENSIONS:
                continue
            self._input_paths.append(path)
            row = self.file_table.rowCount()
            self.file_table.insertRow(row)
            self.file_table.setItem(row, 0, QTableWidgetItem(os.path.basename(path)))
            self.file_table.setItem(row, 1, QTableWidgetItem("Pending"))
        self.convert_all_btn.setEnabled(bool(self._input_paths))

    def _browse_files(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(self, "Choose audio files")
        if paths:
            self.add_files(paths)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:
        paths = [url.toLocalFile() for url in event.mimeData().urls() if url.isLocalFile()]
        self.add_files(paths)

    def _convert_all(self) -> None:
        fmt = self.format_combo.currentText()
        options = ConversionOptions(format=fmt, sample_rate=44100, bit_depth=16)
        for index, input_path in enumerate(self._input_paths):
            stem, _ = os.path.splitext(input_path)
            output_path = f"{stem}_converted.{fmt}"
            worker = ConvertWorker(index, input_path, output_path, options)
            worker.finished_one.connect(self._on_finished_one)
            worker.failed_one.connect(self._on_failed_one)
            self._workers.append(worker)
            self.file_table.setItem(index, 1, QTableWidgetItem("Converting..."))
            worker.start()

    def _on_finished_one(self, index: int, output_path: str) -> None:
        self.file_table.setItem(index, 1, QTableWidgetItem("Done"))

    def _on_failed_one(self, index: int, message: str) -> None:
        self.file_table.setItem(index, 1, QTableWidgetItem(f"Failed: {message[:60]}"))
