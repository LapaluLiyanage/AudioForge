from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QFrame, QLabel, QLineEdit, QVBoxLayout, QWidget

from audioforge import config
from audioforge.core import queue_db
from audioforge.core.models import ConversionOptions
from audioforge.ui.queue_grid import QueueGrid
from audioforge.ui.widgets import SegmentedRow, make_cta_button
from audioforge.workers.download_worker import DownloadWorker

LOSSLESS_FORMATS = {"wav", "flac"}

FORMAT_OPTIONS = [("WAV", "wav"), ("FLAC", "flac"), ("MP3", "mp3")]
QUALITY_OPTIONS = [("44.1/16", (44100, 16)), ("48/24", (48000, 24)), ("96/24", (96000, 24))]

# Used as the project name / output dir fallback whenever the corresponding
# QSettings key (written by SettingsDialog) is unset or empty -- e.g. before
# the user has ever opened Settings.
DEFAULT_PROJECT_NAME = "Default"


class DownloadTab(QWidget):
    """The 'YouTube downloader' card in the right-hand panel."""

    def __init__(self, db_conn, queue_grid: QueueGrid, parent=None):
        super().__init__(parent)
        self.db_conn = db_conn
        self.queue_grid = queue_grid
        # Keep a strong reference to every running/finished worker so Qt/Python
        # never garbage-collects a DownloadWorker while its background thread
        # is still executing.
        self._workers: dict[int, DownloadWorker] = {}
        # Maps job_id -> its key in queue_grid, so signal handlers can refresh
        # the right card.
        self._job_keys: dict[int, str] = {}

        card = QFrame()
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(18, 18, 18, 18)
        card_layout.setSpacing(14)

        title = QLabel("YouTube downloader")
        title.setObjectName("cardTitle")
        card_layout.addWidget(title)

        url_label = QLabel("Paste a YouTube URL")
        url_label.setObjectName("fieldLabel")
        card_layout.addWidget(url_label)

        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://youtube.com/watch?v=")
        self.url_input.textChanged.connect(self._on_url_changed)
        card_layout.addWidget(self.url_input)

        format_label = QLabel("Format")
        format_label.setObjectName("fieldLabel")
        card_layout.addWidget(format_label)
        self.format_row = SegmentedRow(FORMAT_OPTIONS, default="wav")
        card_layout.addWidget(self.format_row)

        quality_label = QLabel("Quality")
        quality_label.setObjectName("fieldLabel")
        card_layout.addWidget(quality_label)
        self.quality_row = SegmentedRow(QUALITY_OPTIONS, default=(44100, 16))
        card_layout.addWidget(self.quality_row)

        self.download_btn = make_cta_button("Download", primary=True)
        self.download_btn.setEnabled(False)
        self.download_btn.clicked.connect(self._on_add_to_queue)
        card_layout.addWidget(self.download_btn)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(card)

        default_format = QSettings("AudioForge", "AudioForge").value("default_format", "")
        if default_format:
            self.format_row.set_value(default_format)

    def _current_format(self) -> str:
        return self.format_row.value()

    def _current_quality(self) -> tuple[int, int]:
        return self.quality_row.value()

    def _on_url_changed(self, text: str) -> None:
        self.download_btn.setEnabled(bool(text.strip()))

    def _current_options(self) -> ConversionOptions:
        fmt = self._current_format()
        sample_rate, bit_depth = self._current_quality()
        if fmt not in LOSSLESS_FORMATS:
            bit_depth = None
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

        key = f"dl:{job_id}"
        self._job_keys[job_id] = key
        title = url.replace("https://", "").replace("http://", "").rstrip("/")
        if len(title) > 42:
            title = title[:42] + "…"
        meta = f"{options.format} · {options.sample_rate}/{options.bit_depth or '-'} · queued"
        self.queue_grid.add_item(key, title=title, meta=meta, status="queued")

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

    def _on_worker_progress(self, job_id: int, percent: float) -> None:
        key = self._job_keys.get(job_id)
        if key is None:
            return
        self.queue_grid.update_item(key, meta=f"downloading · {percent:.0f}%")

    def _on_worker_status_changed(self, job_id: int, status: str) -> None:
        # No output_path here by design: the "done" status_changed emission
        # always precedes/accompanies a separate `job_finished` signal that
        # carries the output_path (see DownloadWorker). update_status's
        # COALESCE(?, output_path) means this call never clobbers a path
        # already written by the `job_finished` handler below.
        queue_db.update_status(self.db_conn, job_id, status)
        key = self._job_keys.get(job_id)
        if key is not None:
            self.queue_grid.update_item(key, status=status, meta=status)

    def _on_worker_finished(self, job_id: int, output_path: str) -> None:
        queue_db.update_status(self.db_conn, job_id, "done", output_path=output_path)
        self._workers.pop(job_id, None)

    def _on_worker_failed(self, job_id: int, message: str) -> None:
        queue_db.update_status(self.db_conn, job_id, "failed", error_message=message)
        key = self._job_keys.get(job_id)
        if key is not None:
            self.queue_grid.update_item(key, status="failed", meta="failed", error=message)
        self._workers.pop(job_id, None)
