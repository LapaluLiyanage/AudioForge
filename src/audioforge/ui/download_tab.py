from PySide6.QtWidgets import (
    QComboBox, QHBoxLayout, QLineEdit, QPushButton, QTableWidget, QVBoxLayout, QWidget,
)

LOSSLESS_FORMATS = {"wav", "flac"}


class DownloadTab(QWidget):
    def __init__(self, db_conn, parent=None):
        super().__init__(parent)
        self.db_conn = db_conn

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

        self._on_format_changed(self.format_combo.currentText())

    def _on_url_changed(self, text: str) -> None:
        self.add_to_queue_btn.setEnabled(bool(text.strip()))

    def _on_format_changed(self, fmt: str) -> None:
        self.bit_depth_combo.setEnabled(fmt in LOSSLESS_FORMATS)

    def _on_add_to_queue(self) -> None:
        # TODO(sub-plan 6 continuation): spawn ProbeWorker(self.url_input.text()),
        # on success call queue_db.enqueue(self.db_conn, url, project_name, options)
        # and refresh self.queue_table from queue_db.list_jobs(self.db_conn).
        pass
