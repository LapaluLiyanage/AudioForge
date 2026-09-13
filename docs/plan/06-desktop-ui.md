# Desktop UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** A PySide6 main window that lets a user paste a URL, confirm metadata, pick format/quality, watch a batch queue with progress bars, retry failures, and change settings — dark-themed.

**Architecture:** `app.py` creates the `QApplication` and `MainWindow`. `MainWindow` hosts a `QTabWidget` with a "Download" tab (sub-plan 6, this file) and a "Convert" tab (sub-plan 7). A `DownloadWorker(QThread)` wraps `downloader.probe/download_audio` → `converter.convert` → `tagger.write_tags`, emitting Qt signals (`progress(int job_id, float pct)`, `status_changed(int job_id, str status)`, `job_failed(int job_id, str message)`) that the queue-view table connects to. The queue table's data model reads from `queue_db` on every signal (simplest correct approach for MVP; do not build a custom `QAbstractTableModel` diffing engine — re-query and refresh rows).

**Tech Stack:** PySide6 (`QMainWindow`, `QThread`, `QTableWidget`, `QDialog`), `pytest-qt` for UI tests, QSS for dark theme.

**Spec:** [00-overview.md](00-overview.md) §5.1–5.4, §5.8–5.9, [ORIGINAL_BRIEF.md](ORIGINAL_BRIEF.md) §5, §7

## Global Constraints

- No blocking calls on the Qt main thread — all yt-dlp/FFmpeg work happens inside `DownloadWorker(QThread)`.
- First-run disclaimer (`disclaimer_dialog.py`) must block usage of the Download tab until accepted; store acceptance in `QSettings` so it only shows once.
- Dark theme applied globally via a QSS stylesheet loaded once at `QApplication` startup — no per-widget inline styling.
- Settings (output base dir, default format/quality, project name) persisted via `QSettings`, not the jobs DB.

---

### Task 1: App entry point + dark theme

**Files:**
- Create: `src/audioforge/app.py`
- Create: `src/audioforge/ui/theme.py`
- Create: `src/audioforge/ui/main_window.py`

**Interfaces:**
- Produces: `main()` (entry point run via `python -m audioforge.app`), `DARK_STYLESHEET: str`, `class MainWindow(QMainWindow)`.

- [ ] **Step 1: Write `theme.py`**

```python
# src/audioforge/ui/theme.py
"""Dark theme QSS for the whole application."""

DARK_STYLESHEET = """
QWidget { background-color: #1e1f22; color: #e6e6e6; font-size: 13px; }
QMainWindow { background-color: #1e1f22; }
QTabWidget::pane { border: 1px solid #33353a; }
QTabBar::tab { background: #2a2b2e; padding: 8px 16px; color: #c8c8c8; }
QTabBar::tab:selected { background: #3a3d42; color: #ffffff; }
QPushButton { background-color: #3a3d42; border: 1px solid #4a4d52; padding: 6px 12px; border-radius: 4px; }
QPushButton:hover { background-color: #4a4d52; }
QPushButton:disabled { color: #6a6a6a; }
QLineEdit, QComboBox, QSpinBox { background-color: #2a2b2e; border: 1px solid #4a4d52; padding: 4px; border-radius: 3px; }
QTableWidget { background-color: #232427; gridline-color: #33353a; }
QProgressBar { border: 1px solid #4a4d52; border-radius: 3px; text-align: center; }
QProgressBar::chunk { background-color: #5a8fdc; }
QHeaderView::section { background-color: #2a2b2e; padding: 4px; border: none; }
"""
```

- [ ] **Step 2: Write a minimal `MainWindow` (tabs added incrementally in later tasks)**

```python
# src/audioforge/ui/main_window.py
from PySide6.QtWidgets import QMainWindow, QTabWidget


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AudioForge")
        self.resize(900, 600)
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)
```

- [ ] **Step 3: Write `app.py`**

```python
# src/audioforge/app.py
"""AudioForge entry point."""
import sys

from PySide6.QtWidgets import QApplication

from audioforge.ui.main_window import MainWindow
from audioforge.ui.theme import DARK_STYLESHEET


def main() -> int:
    app = QApplication(sys.argv)
    app.setStyleSheet(DARK_STYLESHEET)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Smoke-test manually**

Run: `python -m audioforge.app`
Expected: A dark-themed empty window titled "AudioForge" opens and closes cleanly.

- [ ] **Step 5: Write an automated smoke test**

```python
# tests/ui/test_main_window.py
from audioforge.ui.main_window import MainWindow


def test_main_window_has_correct_title(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)
    assert window.windowTitle() == "AudioForge"
```

Run: `pytest tests/ui/test_main_window.py -v` → 1 passed (requires `pytest-qt`, already in `requirements-dev.txt`)

- [ ] **Step 6: Commit** — `git add src/audioforge/app.py src/audioforge/ui tests/ui && git commit -m "feat: add app entry point, dark theme, and empty main window"`

---

### Task 2: First-run disclaimer dialog

**Files:**
- Create: `src/audioforge/ui/disclaimer_dialog.py`
- Modify: `src/audioforge/app.py`
- Test: `tests/ui/test_disclaimer_dialog.py`

**Interfaces:**
- Produces: `show_disclaimer_if_needed() -> bool` (returns whether the user may proceed) using `QSettings("AudioForge", "AudioForge")` key `"disclaimer_accepted"`.

- [ ] **Step 1: Write the failing test**

```python
# tests/ui/test_disclaimer_dialog.py
from PySide6.QtCore import QSettings

from audioforge.ui.disclaimer_dialog import show_disclaimer_if_needed


def test_disclaimer_skipped_if_already_accepted(qtbot, monkeypatch):
    settings = QSettings("AudioForge", "AudioForgeTest")
    settings.setValue("disclaimer_accepted", True)
    monkeypatch.setattr(
        "audioforge.ui.disclaimer_dialog._settings", lambda: settings
    )

    assert show_disclaimer_if_needed() is True
```

- [ ] **Step 2: Run test, verify fails** — `ModuleNotFoundError`

- [ ] **Step 3: Implement**

```python
# src/audioforge/ui/disclaimer_dialog.py
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QMessageBox

DISCLAIMER_TEXT = (
    "AudioForge downloads audio from third-party sources such as YouTube.\n\n"
    "Downloading copyrighted content may violate the source platform's Terms of Service. "
    "Use AudioForge only for personal reference, practice, or non-distributed production work. "
    "Do not redistribute or monetize downloaded material you do not have rights to.\n\n"
    "Note: downloaded audio quality can never exceed the source platform's own encoding "
    "(typically ~128-256 kbps). Converting to WAV/FLAC preserves that quality losslessly "
    "from that point forward, but does not improve it.\n\n"
    "By clicking Accept, you agree to use this tool responsibly."
)


def _settings() -> QSettings:
    return QSettings("AudioForge", "AudioForge")


def show_disclaimer_if_needed() -> bool:
    settings = _settings()
    if settings.value("disclaimer_accepted", False, type=bool):
        return True

    box = QMessageBox()
    box.setWindowTitle("AudioForge — Usage Disclaimer")
    box.setText(DISCLAIMER_TEXT)
    box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
    box.setDefaultButton(QMessageBox.StandardButton.No)
    accept_btn = box.button(QMessageBox.StandardButton.Yes)
    accept_btn.setText("Accept")
    box.button(QMessageBox.StandardButton.No).setText("Decline && Quit")

    accepted = box.exec() == QMessageBox.StandardButton.Yes
    if accepted:
        settings.setValue("disclaimer_accepted", True)
    return accepted
```

- [ ] **Step 4: Wire into `app.py`**

```python
# modify src/audioforge/app.py — inside main(), after creating `app` and before `window.show()`
from audioforge.ui.disclaimer_dialog import show_disclaimer_if_needed

    if not show_disclaimer_if_needed():
        return 0
```

- [ ] **Step 5: Run test, verify passes**

- [ ] **Step 6: Commit** — `git add src/audioforge/ui/disclaimer_dialog.py src/audioforge/app.py tests/ui/test_disclaimer_dialog.py && git commit -m "feat: add first-run usage disclaimer"`

---

### Task 3: Download tab — URL input, metadata confirmation, format/quality selection

**Files:**
- Create: `src/audioforge/ui/download_tab.py`
- Modify: `src/audioforge/ui/main_window.py` (add tab)
- Test: `tests/ui/test_download_tab.py`

**Interfaces:**
- Consumes: `probe()` from sub-plan 3 (called synchronously for single-metadata lookups is acceptable ONLY behind a `QThread`-based `ProbeWorker`, never on the main thread — implement `ProbeWorker(QThread)` emitting `probed(object)` / `probe_failed(str)`), `ConversionOptions` from sub-plan 2, `enqueue()` from sub-plan 5.
- Produces: `class DownloadTab(QWidget)` with `url_input: QLineEdit`, `format_combo: QComboBox`, `sample_rate_combo: QComboBox`, `bit_depth_combo: QComboBox`, `add_to_queue_btn: QPushButton`, `queue_table: QTableWidget` — consumed by `main_window.py`.

- [ ] **Step 1: Write the failing test (widget construction + enabling logic only — no real network)**

```python
# tests/ui/test_download_tab.py
from audioforge.ui.download_tab import DownloadTab


def test_add_to_queue_disabled_until_url_entered(qtbot):
    tab = DownloadTab(db_conn=None)
    qtbot.addWidget(tab)

    assert not tab.add_to_queue_btn.isEnabled()

    qtbot.keyClicks(tab.url_input, "https://youtube.com/watch?v=abc")

    assert tab.add_to_queue_btn.isEnabled()


def test_bit_depth_disabled_for_lossy_formats(qtbot):
    tab = DownloadTab(db_conn=None)
    qtbot.addWidget(tab)

    tab.format_combo.setCurrentText("mp3")

    assert not tab.bit_depth_combo.isEnabled()

    tab.format_combo.setCurrentText("flac")

    assert tab.bit_depth_combo.isEnabled()
```

- [ ] **Step 2: Run test, verify fails** — `ModuleNotFoundError`

- [ ] **Step 3: Implement** (structure only — the actual probe/enqueue wiring uses `ProbeWorker` + `queue_db.enqueue`, following the pattern below; fill in `_on_add_to_queue` per the Interfaces section using functions from sub-plans 2, 3, 5)

```python
# src/audioforge/ui/download_tab.py
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
```

- [ ] **Step 4: Run test, verify passes** — 2 passed

- [ ] **Step 5: Commit** — `git add src/audioforge/ui/download_tab.py tests/ui/test_download_tab.py && git commit -m "feat: add download tab skeleton with format/quality controls"`

---

### Task 4: `DownloadWorker(QThread)` — wires downloader → converter → tagger → queue_db

**Files:**
- Create: `src/audioforge/workers/download_worker.py`
- Test: `tests/workers/test_download_worker.py`
- Modify: `src/audioforge/ui/download_tab.py` (replace the `_on_add_to_queue` TODO with real wiring: start a `DownloadWorker` per queued job, connect its signals to update `queue_table` rows and `queue_db` status)

**Interfaces:**
- Consumes: `probe`/`download_audio` (sub-plan 3), `convert` (sub-plan 2), `write_tags` (sub-plan 4), `resolve_output_path` (sub-plan 4), `update_status` (sub-plan 5).
- Produces: `class DownloadWorker(QThread)` with signals `progress = Signal(int, float)`, `status_changed = Signal(int, str)`, `failed = Signal(int, str)`, constructed as `DownloadWorker(job_id, url, project_name, options, base_output_dir)`.

- [ ] **Step 1: Write the failing test (mock every core function, assert call order and signal emission)**

```python
# tests/workers/test_download_worker.py
from unittest.mock import patch

from audioforge.core.models import ConversionOptions, TrackMetadata
from audioforge.workers.download_worker import DownloadWorker


@patch("audioforge.workers.download_worker.write_tags")
@patch("audioforge.workers.download_worker.convert")
@patch("audioforge.workers.download_worker.resolve_output_path", return_value="/out/Track.flac")
@patch("audioforge.workers.download_worker.download_audio", return_value="/tmp/raw.webm")
@patch("audioforge.workers.download_worker.probe")
def test_worker_runs_full_pipeline_and_emits_done(
    mock_probe, mock_download, mock_resolve, mock_convert, mock_tag, qtbot
):
    mock_probe.return_value = TrackMetadata(
        id="x", title="Track", uploader="Ch", duration_seconds=10, url="u"
    )
    opts = ConversionOptions(format="flac", sample_rate=44100, bit_depth=16)
    worker = DownloadWorker(job_id=1, url="u", project_name="P", options=opts, base_output_dir="/out")

    statuses = []
    worker.status_changed.connect(lambda job_id, status: statuses.append(status))

    with qtbot.waitSignal(worker.status_changed, timeout=2000):
        worker.start()
    worker.wait()

    assert "downloading" in statuses
    assert "converting" in statuses
    assert "done" in statuses
    mock_convert.assert_called_once()
    mock_tag.assert_called_once()


@patch("audioforge.workers.download_worker.probe", side_effect=Exception("boom"))
def test_worker_emits_failed_on_exception(mock_probe, qtbot):
    from audioforge.core.models import ConversionOptions
    opts = ConversionOptions(format="mp3", sample_rate=44100, bit_depth=None)
    worker = DownloadWorker(job_id=2, url="u", project_name="P", options=opts, base_output_dir="/out")

    with qtbot.waitSignal(worker.failed, timeout=2000) as blocker:
        worker.start()
    worker.wait()

    assert blocker.args[0] == 2
    assert "boom" in blocker.args[1]
```

- [ ] **Step 2: Run test, verify fails** — `ModuleNotFoundError`

- [ ] **Step 3: Implement**

```python
# src/audioforge/workers/download_worker.py
from __future__ import annotations

import tempfile
from datetime import date

from PySide6.QtCore import QThread, Signal

from audioforge.core.converter import convert
from audioforge.core.downloader import download_audio, probe
from audioforge.core.models import ConversionOptions
from audioforge.core.organizer import resolve_output_path
from audioforge.core.tagger import write_tags


class DownloadWorker(QThread):
    progress = Signal(int, float)
    status_changed = Signal(int, str)
    failed = Signal(int, str)

    def __init__(self, job_id: int, url: str, project_name: str, options: ConversionOptions, base_output_dir: str):
        super().__init__()
        self.job_id = job_id
        self.url = url
        self.project_name = project_name
        self.options = options
        self.base_output_dir = base_output_dir

    def run(self) -> None:
        try:
            self.status_changed.emit(self.job_id, "downloading")
            metadata = probe(self.url)
            with tempfile.TemporaryDirectory() as tmp_dir:
                raw_path = download_audio(
                    self.url, tmp_dir, on_progress=lambda pct: self.progress.emit(self.job_id, pct)
                )

                self.status_changed.emit(self.job_id, "converting")
                output_path = resolve_output_path(
                    self.base_output_dir, self.project_name, metadata, self.options.format
                )
                convert(raw_path, output_path, self.options)

                self.status_changed.emit(self.job_id, "tagging")
                write_tags(output_path, metadata, self.options.format, date.today().isoformat())

            self.status_changed.emit(self.job_id, "done")
        except Exception as exc:
            self.failed.emit(self.job_id, str(exc))
```

- [ ] **Step 4: Run test, verify passes** — 2 passed

- [ ] **Step 5: Wire into `download_tab.py`'s `_on_add_to_queue`**

Replace the `TODO` body with: enqueue the job via `queue_db.enqueue`, instantiate `DownloadWorker`, connect its signals to a method that calls `queue_db.update_status` and refreshes the matching `queue_table` row, keep a reference to running workers in `self._workers: dict[int, DownloadWorker]` so they aren't garbage-collected mid-run.

- [ ] **Step 6: Commit** — `git add src/audioforge/workers tests/workers src/audioforge/ui/download_tab.py && git commit -m "feat: wire DownloadWorker pipeline into download tab"`

---

### Task 5: Settings dialog

**Files:**
- Create: `src/audioforge/ui/settings_dialog.py`
- Test: `tests/ui/test_settings_dialog.py`

**Interfaces:**
- Produces: `class SettingsDialog(QDialog)` reading/writing `QSettings` keys `output_base_dir`, `default_format`, `default_project_name`; includes an "Update yt-dlp engine" button calling `downloader.update_ytdlp()` inside a small `QThread` (reuse the `ProbeWorker` pattern — do not block the UI thread on pip).

- [ ] **Step 1: Write the failing test**

```python
# tests/ui/test_settings_dialog.py
from PySide6.QtCore import QSettings

from audioforge.ui.settings_dialog import SettingsDialog


def test_settings_dialog_loads_and_saves_output_dir(qtbot, tmp_path):
    settings = QSettings("AudioForge", "AudioForgeTestSettings")
    dialog = SettingsDialog(settings=settings)
    qtbot.addWidget(dialog)

    dialog.output_dir_input.setText(str(tmp_path))
    dialog.save()

    assert settings.value("output_base_dir") == str(tmp_path)
```

- [ ] **Step 2: Run test, verify fails** — `ModuleNotFoundError`

- [ ] **Step 3: Implement**

```python
# src/audioforge/ui/settings_dialog.py
from PySide6.QtWidgets import QDialog, QFileDialog, QHBoxLayout, QLineEdit, QPushButton, QVBoxLayout


class SettingsDialog(QDialog):
    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.setWindowTitle("Settings")

        self.output_dir_input = QLineEdit(settings.value("output_base_dir", ""))
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self._browse)

        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self._on_save_clicked)

        dir_row = QHBoxLayout()
        dir_row.addWidget(self.output_dir_input)
        dir_row.addWidget(browse_btn)

        layout = QVBoxLayout(self)
        layout.addLayout(dir_row)
        layout.addWidget(save_btn)

    def _browse(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Choose output folder")
        if path:
            self.output_dir_input.setText(path)

    def save(self) -> None:
        self.settings.setValue("output_base_dir", self.output_dir_input.text())

    def _on_save_clicked(self) -> None:
        self.save()
        self.accept()
```

- [ ] **Step 4: Run test, verify passes**

- [ ] **Step 5: Commit** — `git add src/audioforge/ui/settings_dialog.py tests/ui/test_settings_dialog.py && git commit -m "feat: add settings dialog for output directory"`
