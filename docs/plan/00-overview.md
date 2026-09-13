# AudioForge — Master Development Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement the sub-plans task-by-task. Each sub-plan below is independently implementable and independently testable.

**Goal:** Ship a Windows desktop app (AudioForge) that lets a music production studio pull reference audio from YouTube and convert/organize it into DAW-ready WAV/FLAC/MP3/etc., plus a standalone local file converter — replacing the studio's current ad-hoc browser-extension/online-converter workflow.

**Architecture:** A PySide6 (Qt for Python) desktop app. The UI never talks to yt-dlp/FFmpeg directly — it enqueues jobs into a SQLite-backed job queue; background `QThread` workers pull jobs, run yt-dlp (download) → FFmpeg (convert) → mutagen (tag) → filesystem (organize into output folders), and report progress back to the UI via Qt signals. A local drag-and-drop converter reuses the same conversion worker, skipping the download step.

**Tech Stack:** Python 3.11+, PySide6, yt-dlp (as a library), FFmpeg (bundled or system), mutagen, SQLite (`sqlite3` stdlib), pytest, PyInstaller + Inno Setup for distribution.

**Spec:** This plan implements the project brief the client/researcher wrote, reproduced in full at `docs/plan/ORIGINAL_BRIEF.md`.

## Global Constraints

- Primary OS target: Windows 10/11. No macOS/Linux work in MVP.
- No telemetry, no network calls except the download step itself.
- All long-running work (network, encode) MUST run off the Qt main thread — the UI must never freeze.
- Output audio quality must not be re-encoded lossily more than once (avoid MP3→MP3 or unnecessary transcodes when the source is already in the target format).
- First-run disclaimer about YouTube ToS/copyright is mandatory before any download can start.
- yt-dlp version must be independently upgradable without reinstalling the app (in-app "Update engine" action).
- Every core module (downloader, converter, tagger, queue) must have unit tests using pytest; no network calls in unit tests — use local fixture files and mock yt-dlp/ffmpeg where the test is about our glue code, not about yt-dlp/ffmpeg themselves.

## Sub-Plans (execute in this order)

| # | Plan file | Delivers |
|---|---|---|
| 1 | [01-environment-setup.md](01-environment-setup.md) | Repo skeleton, dependency management, dev tooling, CI-less local test runner |
| 2 | [02-conversion-engine.md](02-conversion-engine.md) | FFmpeg wrapper: format/sample-rate/bit-depth conversion, used by both download pipeline and local converter |
| 3 | [03-download-engine.md](03-download-engine.md) | yt-dlp wrapper: metadata probe, single/playlist download, progress callbacks, engine self-update |
| 4 | [04-metadata-tagging.md](04-metadata-tagging.md) | mutagen-based tagging + output folder/naming organizer |
| 5 | [05-job-queue-persistence.md](05-job-queue-persistence.md) | SQLite job queue: schema, CRUD, status transitions, retry logic |
| 6 | [06-desktop-ui.md](06-desktop-ui.md) | PySide6 app shell: URL input, queue view, progress bars, settings, dark theme, first-run disclaimer |
| 7 | [07-local-file-converter.md](07-local-file-converter.md) | Drag-and-drop local conversion tab, reusing the conversion engine |
| 8 | [08-packaging-distribution.md](08-packaging-distribution.md) | PyInstaller build + Inno Setup installer, versioning |
| 9 | [09-phase2-roadmap.md](09-phase2-roadmap.md) | Backlog only (not scheduled for MVP): normalization, DAW watch-folder, auto-update, stems |

## Directory Layout (locked in during planning)

```
AudioForge/
  docs/plan/                  # this plan
  src/audioforge/
    __init__.py
    app.py                    # entry point, creates QApplication
    config.py                 # paths, defaults, settings persistence
    core/
      __init__.py
      models.py                # dataclasses: TrackMetadata, Job, JobStatus
      converter.py             # FFmpeg wrapper
      downloader.py             # yt-dlp wrapper
      tagger.py                 # mutagen wrapper
      organizer.py               # output path/filename resolution
      queue_db.py                # SQLite job queue
    workers/
      __init__.py
      download_worker.py         # QThread: full download+convert+tag pipeline
      convert_worker.py          # QThread: local-file-only conversion
    ui/
      __init__.py
      main_window.py
      download_tab.py
      converter_tab.py
      settings_dialog.py
      disclaimer_dialog.py
      theme.py                    # dark theme QSS
  tests/
    core/
    workers/
  requirements.txt
  pyproject.toml
  README.md
  .gitignore
```

## Milestone Roadmap (from the original brief, kept for reference)

| Phase | Est. duration | Deliverable |
|---|---|---|
| 1. Setup & Spike | 1 week | Repo skeleton + yt-dlp/FFmpeg proof-of-concept |
| 2. Core MVP | 3 weeks | Sub-plans 2–6 |
| 3. Local converter + polish | 1 week | Sub-plan 7 + dark theme polish |
| 4. Packaging | 3–4 days | Sub-plan 8 |
| 5. Studio pilot | 1 week | Bugfixes from real usage |
| 6. Phase 2 | Ongoing | Sub-plan 9 backlog |

Status tracking for each sub-plan lives in that sub-plan's own checkboxes — update this table only when a whole phase completes.

**Phase status:** Phase 1 (environment setup) — in progress, started 2026-09-14.
