"""QThread worker that runs the full download -> convert -> tag pipeline for one job.

This worker MUST NOT touch ``queue_db`` (or any sqlite3.Connection) directly:
sqlite3 connections are owned by the thread that created them, and
``DownloadWorker.run()`` executes on a background thread. All queue_db
reads/writes happen in the main/UI thread's slots, driven by the signals
emitted here.

For a real QObject receiver (e.g. a bound method on a QWidget living in the
main thread, as ``download_tab.py`` uses), Qt's Auto-Connection resolves the
*receiver's own* thread affinity and correctly delivers these cross-thread
signals via a QueuedConnection, running the slot on the main/UI thread as
required. See the ``moveToThread(self)`` call in ``__init__`` for a note on
plain-callable receivers (used only in tests).
"""
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
    # Emitted once, alongside the "done" status_changed emission, carrying the
    # resolved output_path so the UI-thread slot can persist it via
    # queue_db.update_status(..., output_path=...). status_changed alone never
    # carries output_path, so without this signal the queue_db "done" row's
    # output_path would stay NULL forever.
    # Named job_finished (not `finished`) because QThread already defines its
    # own `finished` signal; reusing that name would shadow the inherited one
    # and make the standard worker.finished.connect(worker.deleteLater)
    # cleanup idiom unavailable on this subclass.
    job_finished = Signal(int, str)
    failed = Signal(int, str)

    def __init__(self, job_id: int, url: str, project_name: str, options: ConversionOptions, base_output_dir: str):
        super().__init__()
        self.job_id = job_id
        self.url = url
        self.project_name = project_name
        self.options = options
        self.base_output_dir = base_output_dir
        # QThread quirk: a QThread *subclass instance* keeps living in the
        # thread that constructed it (the creator/main thread) even while its
        # overridden run() executes on the new OS thread. When a signal is
        # connected to a receiver with no QObject thread affinity of its own
        # (a bare function/lambda, as the unit tests below use), PySide falls
        # back to the *sender's* declared thread affinity to decide
        # Direct-vs-Queued delivery. Left at the default, that means such
        # receivers would be queued onto the main thread's event loop, which
        # is never pumped between `worker.start()` and `worker.wait()` in a
        # synchronous test, so emissions after the first would silently sit
        # undelivered. Re-homing this object onto itself (the thread it will
        # actually run on) makes such receivers execute synchronously/inline
        # as the pipeline progresses. This has no effect on real QObject
        # receivers (e.g. DownloadTab's bound-method slots): Qt resolves
        # *their own* thread affinity regardless of the sender's, so they are
        # still correctly queued back onto the main/UI thread.
        self.moveToThread(self)

    def run(self) -> None:
        try:
            self.status_changed.emit(self.job_id, "downloading")
            metadata = probe(self.url)
            if isinstance(metadata, list):
                raise ValueError(
                    "Playlist URLs are not supported yet — please paste a single video URL."
                )
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

            self.job_finished.emit(self.job_id, output_path)
            self.status_changed.emit(self.job_id, "done")
        except Exception as exc:
            self.failed.emit(self.job_id, str(exc))
