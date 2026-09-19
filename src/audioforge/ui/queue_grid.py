"""Unified card-grid queue view shared by the download and convert forms."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame, QGridLayout, QHBoxLayout, QLabel, QScrollArea, QSizePolicy, QVBoxLayout, QWidget,
)

from audioforge.ui import theme

_BUSY_STATUSES = {"downloading", "converting", "tagging"}

_DOT_COLORS = {
    "queued": "#565C5E",
    "downloading": theme.ACCENT,
    "converting": theme.ACCENT,
    "tagging": theme.ACCENT,
    "done": theme.TEAL,
    "failed": theme.RED,
}


def _dot_color(status: str) -> str:
    return _DOT_COLORS.get(status, "#565C5E")


class QueueCard(QFrame):
    def __init__(self, title: str, meta: str, status: str, error: str | None = None, parent=None):
        super().__init__(parent)
        self.setObjectName("queueCard")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Waveform-placeholder art area. Dot/title are laid out via plain
        # QHBoxLayouts (no intermediate QWidget) so the app-wide
        # `QWidget { background-color: ... }` rule has nothing to paint over
        # this frame's own #queueArt background.
        art = QFrame()
        art.setObjectName("queueArt")
        art.setFixedHeight(96)
        art_layout = QVBoxLayout(art)
        art_layout.setContentsMargins(10, 10, 10, 10)
        art_layout.setSpacing(0)

        self._dot = QLabel()
        self._dot.setFixedSize(9, 9)
        dot_row = QHBoxLayout()
        dot_row.addStretch(1)
        dot_row.addWidget(self._dot)
        art_layout.addLayout(dot_row)

        self._waveform_label = QLabel("waveform")
        self._waveform_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._waveform_label.setStyleSheet(
            f"background: transparent; color: {theme.TEXT_FAINT}; "
            f"font-family: {theme.FONT_MONO}; font-size: 10px;"
        )
        art_layout.addWidget(self._waveform_label, 1)

        self._title_label = QLabel()
        self._title_label.setWordWrap(False)
        self._title_label.setStyleSheet(
            f"background: rgba(15,17,18,0.72); padding: 5px 10px; border-radius: 100px; "
            f"font-size: 11px; color: {theme.TEXT_PRIMARY};"
        )
        title_row = QHBoxLayout()
        title_row.addWidget(self._title_label)
        title_row.addStretch(1)
        art_layout.addLayout(title_row)

        layout.addWidget(art)

        self._meta_label = QLabel()
        self._meta_label.setObjectName("cardMeta")
        meta_row = QWidget()
        meta_row.setStyleSheet("background: transparent;")
        meta_layout = QVBoxLayout(meta_row)
        meta_layout.setContentsMargins(14, 10, 14, 10)
        meta_layout.addWidget(self._meta_label)
        layout.addWidget(meta_row)

        self._error_label = QLabel()
        self._error_label.setObjectName("cardError")
        self._error_label.setWordWrap(True)
        self._error_row = QWidget()
        self._error_row.setStyleSheet("background: transparent;")
        error_layout = QVBoxLayout(self._error_row)
        error_layout.setContentsMargins(14, 0, 14, 12)
        error_layout.addWidget(self._error_label)
        layout.addWidget(self._error_row)
        self._error_row.hide()

        self.update_content(title, meta, status, error)

    def update_content(self, title: str, meta: str, status: str, error: str | None = None) -> None:
        self._title_label.setText(title)
        self._title_label.setToolTip(title)
        self._meta_label.setText(meta)
        self._dot.setStyleSheet(f"background: {_dot_color(status)}; border-radius: 4px;")
        if error:
            self._error_label.setText(error)
            self._error_row.show()
        else:
            self._error_row.hide()


class QueueGrid(QWidget):
    """Two-column card grid of download/convert jobs, keyed by an opaque string id."""

    changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._cards: dict[str, QueueCard] = {}
        self._fields: dict[str, dict] = {}
        self._order: list[str] = []

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        self._empty_label = QLabel("Nothing queued yet. Paste a link or drop a file to start.")
        self._empty_label.setObjectName("emptyState")
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        outer.addWidget(self._empty_label)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self._grid_host = QWidget()
        self._grid = QGridLayout(self._grid_host)
        self._grid.setSpacing(16)
        self._grid.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._grid_host.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        scroll.setWidget(self._grid_host)
        outer.addWidget(scroll)
        self._scroll = scroll
        self._scroll.hide()

    def add_item(self, key: str, title: str, meta: str, status: str = "queued", error: str | None = None) -> None:
        card = QueueCard(title, meta, status, error)
        self._cards[key] = card
        self._fields[key] = {"title": title, "meta": meta, "status": status, "error": error}
        self._order.insert(0, key)
        self._relayout()
        self.changed.emit()

    def update_item(self, key: str, status: str | None = None, meta: str | None = None, error: str | None = None) -> None:
        card = self._cards.get(key)
        fields = self._fields.get(key)
        if card is None or fields is None:
            return
        if status is not None:
            fields["status"] = status
        if meta is not None:
            fields["meta"] = meta
        if error is not None:
            fields["error"] = error
        card.update_content(fields["title"], fields["meta"], fields["status"], fields["error"])
        self.changed.emit()

    def get_status(self, key: str) -> str | None:
        fields = self._fields.get(key)
        return fields["status"] if fields else None

    def has_active_items(self) -> bool:
        return any(f["status"] in _BUSY_STATUSES for f in self._fields.values())

    def _relayout(self) -> None:
        while self._grid.count():
            item = self._grid.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(self._grid_host)

        columns = 2
        for index, key in enumerate(self._order):
            row, col = divmod(index, columns)
            self._grid.addWidget(self._cards[key], row, col)

        has_items = bool(self._order)
        self._empty_label.setVisible(not has_items)
        self._scroll.setVisible(has_items)
