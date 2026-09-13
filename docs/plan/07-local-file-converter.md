# Local File Converter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** A "Convert" tab where the user drags in existing local audio files and converts them to a target format/quality, without touching yt-dlp or the job queue DB.

**Architecture:** `ConvertTab(QWidget)` accepts drag-and-drop files via `dragEnterEvent`/`dropEvent`, lists them in a table, and runs each through a lightweight `ConvertWorker(QThread)` that calls `converter.convert()` directly (no download step, no tagging, no queue_db — this is a stateless one-off tool distinct from the download pipeline).

**Tech Stack:** PySide6 drag-and-drop (`QWidget.setAcceptDrops(True)`, `QDropEvent.mimeData().urls()`).

**Spec:** [00-overview.md](00-overview.md) §5.7, [ORIGINAL_BRIEF.md](ORIGINAL_BRIEF.md) §5.7

## Global Constraints

- Reuses `ConversionOptions`/`convert()` from sub-plan 2 — do not duplicate conversion logic.
- Output files are written next to the source file by default, with a filename suffix (`_converted`), unless the user picks a different output folder.
- Only accept file extensions FFmpeg can read as audio; reject non-audio drops with an inline message instead of silently failing.

---

### Task 1: `ConvertWorker(QThread)`

**Files:**
- Create: `src/audioforge/workers/convert_worker.py`
- Test: `tests/workers/test_convert_worker.py`

**Interfaces:**
- Consumes: `convert()`, `ConversionOptions` from sub-plan 2.
- Produces: `class ConvertWorker(QThread)` with signals `progress = Signal(int, float)` (index into a batch), `finished_one = Signal(int, str)` (index, output path), `failed_one = Signal(int, str)` (index, error message); constructed as `ConvertWorker(index, input_path, output_path, options)`.

- [ ] **Step 1: Write the failing test**

```python
# tests/workers/test_convert_worker.py
from unittest.mock import patch

from audioforge.core.models import ConversionOptions
from audioforge.workers.convert_worker import ConvertWorker


@patch("audioforge.workers.convert_worker.convert")
def test_convert_worker_emits_finished_one_on_success(mock_convert, qtbot):
    mock_convert.return_value.output_path = "/out/file.flac"
    opts = ConversionOptions(format="flac", sample_rate=44100, bit_depth=16)
    worker = ConvertWorker(index=0, input_path="/in/file.wav", output_path="/out/file.flac", options=opts)

    with qtbot.waitSignal(worker.finished_one, timeout=2000) as blocker:
        worker.start()
    worker.wait()

    assert blocker.args == [0, "/out/file.flac"]


@patch("audioforge.workers.convert_worker.convert", side_effect=Exception("bad file"))
def test_convert_worker_emits_failed_one_on_error(mock_convert, qtbot):
    opts = ConversionOptions(format="mp3", sample_rate=44100, bit_depth=None)
    worker = ConvertWorker(index=1, input_path="/in/broken", output_path="/out/broken.mp3", options=opts)

    with qtbot.waitSignal(worker.failed_one, timeout=2000) as blocker:
        worker.start()
    worker.wait()

    assert blocker.args == [1, "bad file"]
```

- [ ] **Step 2: Run test, verify fails** — `ModuleNotFoundError`

- [ ] **Step 3: Implement**

```python
# src/audioforge/workers/convert_worker.py
from PySide6.QtCore import QThread, Signal

from audioforge.core.converter import convert
from audioforge.core.models import ConversionOptions


class ConvertWorker(QThread):
    progress = Signal(int, float)
    finished_one = Signal(int, str)
    failed_one = Signal(int, str)

    def __init__(self, index: int, input_path: str, output_path: str, options: ConversionOptions):
        super().__init__()
        self.index = index
        self.input_path = input_path
        self.output_path = output_path
        self.options = options

    def run(self) -> None:
        try:
            result = convert(self.input_path, self.output_path, self.options)
            self.finished_one.emit(self.index, result.output_path)
        except Exception as exc:
            self.failed_one.emit(self.index, str(exc))
```

- [ ] **Step 4: Run test, verify passes** — 2 passed

- [ ] **Step 5: Commit** — `git add src/audioforge/workers/convert_worker.py tests/workers/test_convert_worker.py && git commit -m "feat: add standalone ConvertWorker for local file conversion"`

---

### Task 2: `ConvertTab` with drag-and-drop

**Files:**
- Create: `src/audioforge/ui/converter_tab.py`
- Modify: `src/audioforge/ui/main_window.py` (add second tab)
- Test: `tests/ui/test_converter_tab.py`

**Interfaces:**
- Consumes: `ConvertWorker` from Task 1, `ConversionOptions` from sub-plan 2.
- Produces: `class ConverterTab(QWidget)` with `file_table: QTableWidget`, `format_combo: QComboBox`, `convert_all_btn: QPushButton`, `add_files(paths: list[str]) -> None` (public method so both drag-and-drop and a manual "Add Files..." button share the same entry point, and so tests can bypass real drag events).

- [ ] **Step 1: Write the failing test (test `add_files` directly — do not simulate real OS drag-and-drop, which pytest-qt cannot do reliably)**

```python
# tests/ui/test_converter_tab.py
from audioforge.ui.converter_tab import ConverterTab


def test_add_files_populates_table(qtbot):
    tab = ConverterTab()
    qtbot.addWidget(tab)

    tab.add_files(["/music/track1.wav", "/music/track2.mp3"])

    assert tab.file_table.rowCount() == 2
    assert tab.file_table.item(0, 0).text() == "track1.wav"


def test_convert_all_disabled_when_no_files(qtbot):
    tab = ConverterTab()
    qtbot.addWidget(tab)
    assert not tab.convert_all_btn.isEnabled()

    tab.add_files(["/music/track1.wav"])
    assert tab.convert_all_btn.isEnabled()
```

- [ ] **Step 2: Run test, verify fails** — `ModuleNotFoundError`

- [ ] **Step 3: Implement**

```python
# src/audioforge/ui/converter_tab.py
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
```

- [ ] **Step 4: Run test, verify passes** — 2 passed

- [ ] **Step 5: Add the tab to `MainWindow`**

```python
# modify src/audioforge/ui/main_window.py
from audioforge.ui.converter_tab import ConverterTab
# ... inside __init__, after creating self.tabs:
        self.tabs.addTab(ConverterTab(), "Convert")
```

- [ ] **Step 6: Commit** — `git add src/audioforge/ui/converter_tab.py src/audioforge/ui/main_window.py tests/ui/test_converter_tab.py && git commit -m "feat: add drag-and-drop local file converter tab"`
