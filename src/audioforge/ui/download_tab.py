from PySide6.QtCore import QSettings
from PySide6.QtWidgets import (
    QComboBox, QHBoxLayout, QLineEdit, QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from audioforge import config
from audioforge.core import queue_db
from audioforge.core.models import ConversionOptions
from audioforge.workers.download_worker import DownloadWorker

LOSSLESS_FORMATS = {"wav", "flac"}

# Used as the project name / output dir fallback whenever the corresponding
# QSettings key (written by SettingsDialog) is unset or empty -- e.g. before
# the user has ever opened Settings.
DEFAULT_PROJECT_NAME = "Default"

_COL_TITLE = 0
_COL_FORMAT = 1
_COL_STATUS = 2
_COL_PROGRESS = 3


class DownloadTab(QWidget):
    def __init__(self, db_conn, parent=None):
        super().__init__(parent)
        self.db_conn = db_conn
        # Keep a strong reference to every running/finished worker so Qt/Python
        # never garbage-collects a DownloadWorker while its background thread
        # is still executing.
        self._workers: dict[int, DownloadWorker] = {}
        # Maps job_id -> its row index in queue_table, so signal handlers can
        # refresh the right row.
        self._job_rows: dict[int, int] = {}

        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("Paste a YouTube URL...")
        self.format_combo = QComboBox()
        self.format_combo.addItems(["wav", "flac", "mp3", "m4a", "opus"])
        self.sample_rate_combo = QComboBox()
        self.sample_rate_combo.addItems(["44100", "48000", "96000"])
        self.bit_depth_combo = QComboBox()
        self.bit_depth_combo.addItems(["16", "24"])
        self.add_to_queue_btn = QPushButton("Add to Queue")
        self.add_to_queue_btn.setEnabled(False)
        self.queue_table = QTableWidget(0, 4)
        self.queue_table.setHorizontalHeaderLabels(["Title", "Format", "Status", "Progress"])

        self.url_input.textChanged.connect(self._on_url_changed)
        self.format_combo.currentTextChanged.connect(self._on_format_changed)
        self.add_to_queue_btn.clicked.connect(self._on_add_to_queue)

        top_row = QHBoxLayout()
        top_row.addWidget(self.url_input)
        top_row.addWidget(self.format_combo)
        top_row.addWidget(self.sample_rate_combo)
        top_row.addWidget(self.bit_depth_combo)
        top_row.addWidget(self.add_to_queue_btn)

        layout = QVBoxLayout(self)
        layout.addLayout(top_row)
        layout.addWidget(self.queue_table)

        default_format = QSettings("AudioForge", "AudioForge").value("default_format", "")
        if default_format:
            index = self.format_combo.findText(default_format)
            if index >= 0:
                self.format_combo.setCurrentIndex(index)

        self._on_format_changed(self.format_combo.currentText())

    def _on_url_changed(self, text: str) -> None:
        self.add_to_queue_btn.setEnabled(bool(text.strip()))

    def _on_format_changed(self, fmt: str) -> None:
        self.bit_depth_combo.setEnabled(fmt in LOSSLESS_FORMATS)

    def _current_options(self) -> ConversionOptions:
        fmt = self.format_combo.currentText()
        sample_rate = int(self.sample_rate_combo.currentText())
        bit_depth = int(self.bit_depth_combo.currentText()) if self.bit_depth_combo.isEnabled() else None
        return ConversionOptions(format=fmt, sample_rate=sample_rate, bit_depth=bit_depth)

    def _on_add_to_queue(self) -> None:
        url = self.url_input.text().strip()
        if not url:
            return
        options = self._current_options()

        settings = QSettings("AudioForge", "AudioForge")
        project_name = settings.value("default_project_name", "") or DEFAULT_PROJECT_NAME
        base_output_dir = settings.value("output_base_dir", "") or config.get_default_output_dir()

        job_id = queue_db.enqueue(self.db_conn, url, project_name, options)

        row = self.queue_table.rowCount()
        self.queue_table.insertRow(row)
        self.queue_table.setItem(row, _COL_TITLE, QTableWidgetItem(url))
        self.queue_table.setItem(row, _COL_FORMAT, QTableWidgetItem(options.format))
        self.queue_table.setItem(row, _COL_STATUS, QTableWidgetItem("queued"))
        self.queue_table.setItem(row, _COL_PROGRESS, QTableWidgetItem("0%"))
        self._job_rows[job_id] = row

        worker = DownloadWorker(
            job_id=job_id,
            url=url,
            project_name=project_name,
            options=options,
            base_output_dir=base_output_dir,
        )
        worker.progress.connect(self._on_worker_progress)
        worker.status_changed.connect(self._on_worker_status_changed)
        worker.job_finished.connect(self._on_worker_finished)
        worker.failed.connect(self._on_worker_failed)
        self._workers[job_id] = worker

        self.url_input.clear()
        worker.start()

    def shutdown(self) -> None:
        """Give any still-running workers a brief chance to finish before the
        window closes. Called from MainWindow.closeEvent -- destroying a
        QThread while it's still running aborts with a Qt warning, so we wait
        (with a timeout) rather than dropping references immediately.
        """
        for worker in list(self._workers.values()):
            if worker.isRunning():
                worker.wait(3000)

    def _set_row_text(self, job_id: int, column: int, text: str) -> None:
        row = self._job_rows.get(job_id)
        if row is None:
            return
        item = self.queue_table.item(row, column)
        if item is None:
            item = QTableWidgetItem()
            self.queue_table.setItem(row, column, item)
        item.setText(text)

    def _on_worker_progress(self, job_id: int, percent: float) -> None:
        self._set_row_text(job_id, _COL_PROGRESS, f"{percent:.0f}%")

    def _on_worker_status_changed(self, job_id: int, status: str) -> None:
        # No output_path here by design: the "done" status_changed emission
        # always precedes/accompanies a separate `job_finished` signal that
        # carries the output_path (see DownloadWorker). update_status's
        # COALESCE(?, output_path) means this call never clobbers a path
        # already written by the `job_finished` handler below.
        queue_db.update_status(self.db_conn, job_id, status)
        self._set_row_text(job_id, _COL_STATUS, status)

    def _on_worker_finished(self, job_id: int, output_path: str) -> None:
        queue_db.update_status(self.db_conn, job_id, "done", output_path=output_path)
        self._workers.pop(job_id, None)

    def _on_worker_failed(self, job_id: int, message: str) -> None:
        queue_db.update_status(self.db_conn, job_id, "failed", error_message=message)
        self._set_row_text(job_id, _COL_STATUS, "failed")
        self._workers.pop(job_id, None)
