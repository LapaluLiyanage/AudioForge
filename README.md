# AudioForge

Desktop audio downloader & converter for music production studios. Pull
reference audio from YouTube and convert/organize it into DAW-ready
WAV/FLAC/MP3, or batch-convert local files — all from one queue. Built to
replace an ad-hoc mix of browser extensions and online converters with a
single offline desktop tool.

## Features

- **YouTube downloader** — paste a URL, pick a format (WAV/FLAC/MP3) and
  quality (44.1 kHz/16-bit, 48 kHz/24-bit, or 96 kHz/24-bit), and it
  downloads, converts, tags, and files the track automatically.
- **Local file converter** — drag and drop (or browse for) audio files
  (WAV, AIFF, MP3, M4A, FLAC, AAC, OGG, Opus, WMA, WebM) and batch-convert
  them to your target format/quality.
- **Unified queue** — downloads and conversions share one card-grid queue
  showing live status (queued/downloading/converting/tagging/done/failed)
  and any error messages inline.
- **Automatic tagging & organizing** — converted tracks are tagged with
  title/artist/date metadata and filed under a per-project output folder.
- **In-app engine updates** — bump the bundled yt-dlp version from Settings
  without reinstalling the app, so YouTube extraction keeps working as the
  site changes.
- **Dark, studio-friendly UI** — a PySide6 desktop shell with an icon
  sidebar, pill-shaped controls, and a card queue.
- **First-run disclaimer** — a one-time notice about YouTube's Terms of
  Service and copyright responsibility, required before any download starts.

## Requirements

- Windows 10/11 (the only supported OS for now)
- Python 3.11+
- [FFmpeg](https://ffmpeg.org/) available on `PATH` (used for all format/
  sample-rate/bit-depth conversion)

## Development setup

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements-dev.txt
pip install -e .
```

## Running tests

```powershell
pytest
```

Unit tests never hit the network or call real FFmpeg/yt-dlp binaries — they
use local fixture files and mock the external tools, so the suite runs
offline and deterministically.

## Running the app

```powershell
python -m audioforge.app
```

### Where things are stored

- **Job queue database**: `%APPDATA%\AudioForge\audioforge.db` (SQLite)
- **Default output folder**: `~\Music\AudioForge\<project name>\`
- **Settings** (output folder, default format, default project name): Qt
  `QSettings` under the `AudioForge`/`AudioForge` org/app key — on Windows
  this lives in the registry (`HKCU\Software\AudioForge\AudioForge`)

## Architecture

AudioForge is a PySide6 (Qt for Python) app. The UI never talks to yt-dlp or
FFmpeg directly — it enqueues jobs into a SQLite-backed job queue, and
background `QThread` workers pull jobs and run:

```
yt-dlp (download) -> FFmpeg (convert) -> mutagen (tag) -> filesystem (organize)
```

reporting progress back to the UI via Qt signals. Local file conversion
reuses the same conversion worker, skipping the download step. All
long-running work runs off the Qt main thread so the UI never freezes.

```
src/audioforge/
  app.py            entry point
  config.py         paths & settings defaults
  core/             downloader, converter, tagger, organizer, job queue, dep checks
  workers/          QThread workers wrapping core/ for the UI
  ui/               PySide6 widgets, theme, and the main window
```

## Building a Windows installer

See [packaging/](packaging/) — `packaging/build.ps1` runs PyInstaller against
`packaging/audioforge.spec` and then Inno Setup (`packaging/installer.iss`)
to produce a distributable installer.

## Project plan

See [docs/plan/00-overview.md](docs/plan/00-overview.md) for the full
development plan and sub-plan breakdown, or
[docs/plan/09-phase2-roadmap.md](docs/plan/09-phase2-roadmap.md) for
backlog ideas beyond the MVP (loudness normalization, a DAW watch-folder,
auto-update, stem separation).

## Legal

Only download content you have the right to use. Respect YouTube's Terms
of Service and applicable copyright law — AudioForge shows a one-time
disclaimer on first run, but responsibility for what you download rests
with you.
