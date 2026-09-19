import os

from PySide6.QtCore import Qt
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import (
    QFileDialog, QFrame, QHBoxLayout, QLabel, QMessageBox, QVBoxLayout, QWidget,
)

from audioforge.core.models import ConversionOptions
from audioforge.ui.queue_grid import QueueGrid
from audioforge.ui.widgets import SegmentedRow, make_cta_button
from audioforge.workers.convert_worker import ConvertWorker

AUDIO_EXTENSIONS = {".wav", ".mp3", ".flac", ".m4a", ".aac", ".ogg", ".opus", ".wma", ".webm"}

FORMAT_OPTIONS = [("WAV", "wav"), ("FLAC", "flac"), ("MP3", "mp3")]
QUALITY_OPTIONS = [("44.1/16", (44100, 16)), ("48/24", (48000, 24)), ("96/24", (96000, 24))]
LOSSLESS_FORMATS = {"wav", "flac"}


class ConverterTab(QWidget):
    """The 'Converter' card in the right-hand panel, plus its Output folder card."""

    def __init__(self, queue_grid: QueueGrid, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.queue_grid = queue_grid
        self._input_paths: list[str] = []
        # Keep a strong reference to every running/finished worker (keyed by
        # its row index) so Qt/Python never garbage-collects a ConvertWorker
        # while its background thread is still executing. Pruned on
        # completion/failure, mirroring DownloadTab._workers.
        self._workers: dict[int, ConvertWorker] = {}
        self._keys: dict[int, str] = {}
        self.output_dir = ""

        card = QFrame()
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(18, 18, 18, 18)
        card_layout.setSpacing(14)

        title = QLabel("Converter")
        title.setObjectName("cardTitle")
        card_layout.addWidget(title)

        self.dropzone = QFrame()
        self.dropzone.setObjectName("dropzone")
        self.dropzone.setCursor(Qt.CursorShape.PointingHandCursor)
        dz_layout = QVBoxLayout(self.dropzone)
        dz_layout.setContentsMargins(16, 16, 16, 16)
        dz_label = QLabel("Drop a file here — wav, aiff, mp3, m4a, flac\n(or click to browse)")
        dz_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        dz_layout.addWidget(dz_label)
        self.dropzone.mousePressEvent = lambda _event: self._browse_files()
        card_layout.addWidget(self.dropzone)

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

        self.convert_all_btn = make_cta_button("Convert File", primary=False)
        self.convert_all_btn.setEnabled(False)
        self.convert_all_btn.clicked.connect(self._convert_all)
        card_layout.addWidget(self.convert_all_btn)

        self.output_card = QFrame()
        self.output_card.setObjectName("outputCard")
        output_layout = QHBoxLayout(self.output_card)
        output_layout.setContentsMargins(16, 14, 16, 14)
        output_label = QLabel("Output")
        output_label.setObjectName("fieldLabel")
        output_layout.addWidget(output_label)
        output_layout.addStretch(1)
        self._output_path_label = QLabel("(next to source file)")
        self._output_path_label.setStyleSheet("font-family: 'IBM Plex Mono','Consolas',monospace; font-size: 12px;")
        output_layout.addWidget(self._output_path_label)
        change_label = QLabel("Change")
        change_label.setObjectName("fieldLabel")
        change_label.setCursor(Qt.CursorShape.PointingHandCursor)
        change_label.mousePressEvent = lambda _event: self._browse_output_dir()
        output_layout.addWidget(change_label)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(card)

    def _current_options(self) -> ConversionOptions:
        fmt = self.format_row.value()
        sample_rate, bit_depth = self.quality_row.value()
        if fmt not in LOSSLESS_FORMATS:
            bit_depth = None
        return ConversionOptions(format=fmt, sample_rate=sample_rate, bit_depth=bit_depth)

    def add_files(self, paths: list[str]) -> None:
        rejected: list[str] = []
        for path in paths:
            if os.path.splitext(path)[1].lower() not in AUDIO_EXTENSIONS:
                rejected.append(os.path.basename(path))
                continue
            index = len(self._input_paths)
            self._input_paths.append(path)
            key = f"cv:{index}"
            self._keys[index] = key
            self.queue_grid.add_item(
                key, title=os.path.basename(path), meta="pending", status="queued",
            )
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
            self.output_dir = path
            self._output_path_label.setText(path)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:
        event.acceptProposedAction()
        paths = [url.toLocalFile() for url in event.mimeData().urls() if url.isLocalFile()]
        self.add_files(paths)

    def _convert_all(self) -> None:
        options = self._current_options()
        # Disable for the duration of the batch: a second click while workers
        # are still running would start new ConvertWorkers against the same
        # output paths concurrently, corrupting the output files.
        self.convert_all_btn.setEnabled(False)
        for index, input_path in enumerate(self._input_paths):
            # Skip rows already converted, in case _convert_all is invoked
            # again (e.g. re-enabled after a batch) while some rows finished
            # and others are still pending.
            key = self._keys[index]
            if self.queue_grid.get_status(key) == "done":
                continue
            stem = os.path.splitext(os.path.basename(input_path))[0]
            if self.output_dir:
                output_path = os.path.join(self.output_dir, f"{stem}_converted.{options.format}")
            else:
                input_stem, _ = os.path.splitext(input_path)
                output_path = f"{input_stem}_converted.{options.format}"
            worker = ConvertWorker(index, input_path, output_path, options)
            worker.finished_one.connect(self._on_finished_one)
            worker.failed_one.connect(self._on_failed_one)
            self._workers[index] = worker
            self.queue_grid.update_item(key, status="converting", meta="converting")
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
        key = self._keys.get(index)
        if key is not None:
            self.queue_grid.update_item(key, status="done", meta=os.path.basename(output_path))
        self._on_batch_worker_done(index)

    def _on_failed_one(self, index: int, message: str) -> None:
        key = self._keys.get(index)
        if key is not None:
            self.queue_grid.update_item(key, status="failed", meta="failed", error=message)
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
