"""Small reusable widgets shared by the download/convert forms and main window."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QButtonGroup, QHBoxLayout, QPushButton, QWidget


def make_pill_button(text: str) -> QPushButton:
    """A checkable, pill-shaped segmented-control button (QSS selector ``[segment=true]``)."""
    btn = QPushButton(text)
    btn.setCheckable(True)
    btn.setProperty("segment", "true")
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    return btn


def make_cta_button(text: str, primary: bool = True) -> QPushButton:
    btn = QPushButton(text)
    btn.setProperty("cta", "primary" if primary else "secondary")
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    return btn


class SegmentedRow(QWidget):
    """A row of exclusive pill buttons bound to arbitrary option values."""

    def __init__(self, options: list[tuple[str, object]], default: object, parent=None):
        super().__init__(parent)
        self._value = default
        self._buttons: dict[object, QPushButton] = {}

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        for label, value in options:
            btn = make_pill_button(label)
            btn.setChecked(value == default)
            btn.clicked.connect(lambda _checked, v=value: self._select(v))
            self._group.addButton(btn)
            layout.addWidget(btn)
            self._buttons[value] = btn
        layout.addStretch(1)

    def _select(self, value: object) -> None:
        self._value = value

    def value(self) -> object:
        return self._value

    def set_value(self, value: object) -> None:
        btn = self._buttons.get(value)
        if btn is not None:
            btn.setChecked(True)
            self._value = value
