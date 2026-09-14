import os

from PySide6.QtCore import Qt
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import (
    QComboBox, QFileDialog, QHBoxLayout, QLabel, QLineEdit, QMessageBox,
    QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from audioforge.core.models import ConversionOptions
from audioforge.workers.convert_worker import ConvertWorker

AUDIO_EXTENSIONS = {".wav", ".mp3", ".flac", ".m4a", ".aac", ".ogg", ".opus", ".wma", ".webm"}


class ConverterTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self._input_paths: list[str] = []
        # Keep a strong reference to every running/finished worker (keyed by
        # its row index) so Qt/Python never garbage-collects a ConvertWorker
        # while its background thread is still executing. Pruned on
        # completion/failure, mirroring DownloadTab._workers.
        self._workers: dict[int, ConvertWorker] = {}

        self.format_combo = QComboBox()
        self.format_combo.addItems(["wav", "flac", "mp3", "m4a", "opus"])
        add_files_btn = QPushButton("Add Files...")
        add_files_btn.clicked.connect(self._browse_files)
        self.convert_all_btn = QPushButton("Convert All")
        self.convert_all_btn.setEnabled(False)
        self.convert_all_btn.clicked.connect(self._convert_all)

        self.output_dir_input = QLineEdit()
        self.output_dir_input.setPlaceholderText("Output folder (default: next to source file)")
        output_browse_btn = QPushButton("Browse...")
        output_browse_btn.clicked.connect(self._browse_output_dir)

        self.file_table = QTableWidget(0, 2)
        self.file_table.setHorizontalHeaderLabels(["File", "Status"])

        drop_hint = QLabel("Drag and drop audio files here, or use Add Files...")
        drop_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)

        top_row = QHBoxLayout()
        top_row.addWidget(add_files_btn)
        top_row.addWidget(self.format_combo)
        top_row.addWidget(self.convert_all_btn)

        output_row = QHBoxLayout()
        output_row.addWidget(QLabel("Output folder:"))
        output_row.addWidget(self.output_dir_input)
        output_row.addWidget(output_browse_btn)

        layout = QVBoxLayout(self)
        layout.addWidget(drop_hint)
        layout.addLayout(top_row)
        layout.addLayout(output_row)
        layout.addWidget(self.file_table)

    def add_files(self, paths: list[str]) -> None:
        rejected: list[str] = []
        for path in paths:
            if os.path.splitext(path)[1].lower() not in AUDIO_EXTENSIONS:
                rejected.append(os.path.basename(path))
                continue
            self._input_paths.append(path)
            row = self.file_table.rowCount()
            self.file_table.insertRow(row)
            self.file_table.setItem(row, 0, QTableWidgetItem(os.path.basename(path)))
            self.file_table.setItem(row, 1, QTableWidgetItem("Pending"))
        self.convert_all_btn.setEnabled(bool(self._input_paths))
        if rejected:
            QMessageBox.warning(
                self,
                "Unsupported files",
                "The following files were not added because their format is not "
                "supported:\n" + "\n".join(rejected),
            )

    def _browse_files(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(self, "Choose audio files")
        if paths:
            self.add_files(paths)

    def _browse_output_dir(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Choose output folder")
        if path:
            self.output_dir_input.setText(path)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:
        event.acceptProposedAction()
        paths = [url.toLocalFile() for url in event.mimeData().urls() if url.isLocalFile()]
        self.add_files(paths)

    def _convert_all(self) -> None:
        fmt = self.format_combo.currentText()
        output_dir = self.output_dir_input.text().strip()
        # Keep source sample rate / bit depth rather than hardcoding, so we
        # (a) don't silently resample/downsample the user's own files, and
        # (b) let converter.convert()'s skip-reencode fast path fire when the
        # source already matches the requested format (e.g. opus -> opus).
        options = ConversionOptions(format=fmt, sample_rate=None, bit_depth=None)
        # Disable for the duration of the batch: a second click while workers
        # are still running would start new ConvertWorkers against the same
        # output paths concurrently, corrupting the output files.
        self.convert_all_btn.setEnabled(False)
        for index, input_path in enumerate(self._input_paths):
            # Skip rows already converted, in case _convert_all is invoked
            # again (e.g. re-enabled after a batch) while some rows finished
            # and others are still pending.
            status_item = self.file_table.item(index, 1)
            if status_item is not None and status_item.text() == "Done":
                continue
            stem = os.path.splitext(os.path.basename(input_path))[0]
            if output_dir:
                output_path = os.path.join(output_dir, f"{stem}_converted.{fmt}")
            else:
                input_stem, _ = os.path.splitext(input_path)
                output_path = f"{input_stem}_converted.{fmt}"
            worker = ConvertWorker(index, input_path, output_path, options)
            worker.finished_one.connect(self._on_finished_one)
            worker.failed_one.connect(self._on_failed_one)
            self._workers[index] = worker
            self.file_table.setItem(index, 1, QTableWidgetItem("Converting..."))
            worker.start()
        # No workers were started (e.g. all rows already "Done") -- nothing
        # will re-enable the button via a completion handler, so do it here.
        if not self._workers:
            self.convert_all_btn.setEnabled(True)

    def _on_batch_worker_done(self, index: int) -> None:
        self._workers.pop(index, None)
        if not self._workers:
            self.convert_all_btn.setEnabled(True)

    def _on_finished_one(self, index: int, output_path: str) -> None:
        self.file_table.setItem(index, 1, QTableWidgetItem("Done"))
        self._on_batch_worker_done(index)

    def _on_failed_one(self, index: int, message: str) -> None:
        self.file_table.setItem(index, 1, QTableWidgetItem(f"Failed: {message[:60]}"))
        self._on_batch_worker_done(index)

    def shutdown(self) -> None:
        """Give any still-running workers a brief chance to finish before the
        window closes. Called from MainWindow.closeEvent -- destroying a
        QThread while it's still running aborts with a Qt warning, so we wait
        (with a timeout) rather than dropping references immediately.
        """
        for worker in list(self._workers.values()):
            if worker.isRunning():
                worker.wait(3000)
