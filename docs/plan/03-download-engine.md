# Download Engine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Wrap `yt-dlp` to (a) probe a URL for metadata before committing to a download, (b) download best-available audio for a single video or a playlist, reporting progress, and (c) allow the yt-dlp engine itself to be upgraded in-app.

**Architecture:** `probe(url) -> TrackMetadata | list[TrackMetadata]` runs yt-dlp in `extract_flat`/no-download mode. `download_audio(url, dest_dir, on_progress) -> str` (path to the raw downloaded audio file, still in source container) runs yt-dlp with `format="bestaudio/best"` and a progress hook, letting the conversion engine (sub-plan 2) handle the actual format transcode afterward — this avoids yt-dlp's own postprocessor duplicating work our converter already does.

**Tech Stack:** `yt-dlp` Python API (`yt_dlp.YoutubeDL`), not the yt-dlp CLI.

**Spec:** [00-overview.md](00-overview.md) §5.1, §5.4, [ORIGINAL_BRIEF.md](ORIGINAL_BRIEF.md) §5.1, §9(risks)

## Global Constraints

- Never pass yt-dlp's own audio-postprocessing options (`FFmpegExtractAudio`) — sub-plan 2's converter owns all transcoding, so yt-dlp downloads the best raw stream and stops.
- Age-restricted/region-locked/unavailable videos must raise a typed `DownloadError` with a human-readable message, not crash the worker thread.
- Playlist URLs must return a list of `TrackMetadata`; single-video URLs return one `TrackMetadata` (not wrapped in a list) — callers use `isinstance(result, list)` to branch.
- No real network calls in unit tests — mock `yt_dlp.YoutubeDL`.

---

### Task 1: `TrackMetadata` model

**Files:**
- Modify: `src/audioforge/core/models.py` (append to file from sub-plan 2)
- Test: `tests/core/test_models.py` (append)

**Interfaces:**
- Produces: `TrackMetadata(id: str, title: str, uploader: str, duration_seconds: int, url: str, thumbnail_url: str | None)` — consumed by `downloader.py` (this plan), `tagger.py` (sub-plan 4), and the UI's confirmation dialog (sub-plan 6).

- [ ] **Step 1: Write the failing test**

```python
# append to tests/core/test_models.py
from audioforge.core.models import TrackMetadata

def test_track_metadata_holds_expected_fields():
    m = TrackMetadata(
        id="abc123", title="Song Title", uploader="Channel Name",
        duration_seconds=215, url="https://youtube.com/watch?v=abc123",
        thumbnail_url="https://img/thumb.jpg",
    )
    assert m.duration_seconds == 215
    assert m.title == "Song Title"
```

- [ ] **Step 2: Run test, verify fails** — `AttributeError`/`ImportError`

- [ ] **Step 3: Implement**

```python
# append to src/audioforge/core/models.py
@dataclass(frozen=True)
class TrackMetadata:
    id: str
    title: str
    uploader: str
    duration_seconds: int
    url: str
    thumbnail_url: str | None = None


class DownloadError(Exception):
    """Raised when yt-dlp cannot probe or download a URL."""
```

- [ ] **Step 4: Run test, verify passes**

- [ ] **Step 5: Commit** — `git commit -am "feat: add TrackMetadata model and DownloadError"`

---

### Task 2: `probe(url)` — metadata lookup without downloading

**Files:**
- Create: `src/audioforge/core/downloader.py`
- Test: `tests/core/test_downloader.py`

**Interfaces:**
- Consumes: `TrackMetadata`, `DownloadError` from Task 1.
- Produces: `probe(url: str) -> TrackMetadata | list[TrackMetadata]` — consumed by the UI's "confirm before download" step (sub-plan 6) and by `download_worker.py` (sub-plan 3/workers).

- [ ] **Step 1: Write the failing test**

```python
# tests/core/test_downloader.py
from unittest.mock import MagicMock, patch

import pytest

from audioforge.core.downloader import probe
from audioforge.core.models import DownloadError, TrackMetadata

SINGLE_INFO = {
    "id": "abc123", "title": "Song Title", "uploader": "Channel",
    "duration": 215, "webpage_url": "https://youtube.com/watch?v=abc123",
    "thumbnail": "https://img/thumb.jpg",
}

PLAYLIST_INFO = {
    "_type": "playlist",
    "entries": [SINGLE_INFO, {**SINGLE_INFO, "id": "def456", "title": "Song 2"}],
}


@patch("audioforge.core.downloader.yt_dlp.YoutubeDL")
def test_probe_single_video_returns_one_metadata(mock_ydl_cls):
    mock_ydl = MagicMock()
    mock_ydl.extract_info.return_value = SINGLE_INFO
    mock_ydl_cls.return_value.__enter__.return_value = mock_ydl

    result = probe("https://youtube.com/watch?v=abc123")

    assert isinstance(result, TrackMetadata)
    assert result.id == "abc123"
    assert result.duration_seconds == 215


@patch("audioforge.core.downloader.yt_dlp.YoutubeDL")
def test_probe_playlist_returns_list(mock_ydl_cls):
    mock_ydl = MagicMock()
    mock_ydl.extract_info.return_value = PLAYLIST_INFO
    mock_ydl_cls.return_value.__enter__.return_value = mock_ydl

    result = probe("https://youtube.com/playlist?list=xyz")

    assert isinstance(result, list)
    assert len(result) == 2
    assert result[1].title == "Song 2"


@patch("audioforge.core.downloader.yt_dlp.YoutubeDL")
def test_probe_raises_download_error_on_extractor_failure(mock_ydl_cls):
    import yt_dlp
    mock_ydl = MagicMock()
    mock_ydl.extract_info.side_effect = yt_dlp.utils.DownloadError("Video unavailable")
    mock_ydl_cls.return_value.__enter__.return_value = mock_ydl

    with pytest.raises(DownloadError):
        probe("https://youtube.com/watch?v=deadbeef")
```

- [ ] **Step 2: Run test, verify fails** — `ModuleNotFoundError`

- [ ] **Step 3: Implement**

```python
# src/audioforge/core/downloader.py
"""yt-dlp wrapper: metadata probing and raw audio download."""
from __future__ import annotations

from collections.abc import Callable

import yt_dlp

from audioforge.core.models import DownloadError, TrackMetadata


def _to_metadata(info: dict) -> TrackMetadata:
    return TrackMetadata(
        id=info["id"],
        title=info.get("title", "Unknown title"),
        uploader=info.get("uploader", "Unknown"),
        duration_seconds=int(info.get("duration") or 0),
        url=info.get("webpage_url", info.get("url", "")),
        thumbnail_url=info.get("thumbnail"),
    )


def probe(url: str) -> TrackMetadata | list[TrackMetadata]:
    opts = {"quiet": True, "no_warnings": True, "extract_flat": "in_playlist", "skip_download": True}
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
    except yt_dlp.utils.DownloadError as exc:
        raise DownloadError(str(exc)) from exc

    if info.get("_type") == "playlist":
        return [_to_metadata(entry) for entry in info["entries"]]
    return _to_metadata(info)


def download_audio(
    url: str,
    dest_dir: str,
    on_progress: Callable[[float], None] | None = None,
) -> str:
    """Download the best available raw audio stream. Returns the downloaded file path."""
    downloaded_path: dict[str, str] = {}

    def _hook(status: dict) -> None:
        if status["status"] == "downloading" and on_progress:
            total = status.get("total_bytes") or status.get("total_bytes_estimate")
            if total:
                on_progress(status.get("downloaded_bytes", 0) / total * 100)
        elif status["status"] == "finished":
            downloaded_path["path"] = status["filename"]

    opts = {
        "quiet": True,
        "no_warnings": True,
        "format": "bestaudio/best",
        "outtmpl": f"{dest_dir}/%(id)s.%(ext)s",
        "progress_hooks": [_hook],
        "noplaylist": True,
    }
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([url])
    except yt_dlp.utils.DownloadError as exc:
        raise DownloadError(str(exc)) from exc

    if "path" not in downloaded_path:
        raise DownloadError("Download finished but no output file was reported by yt-dlp.")
    return downloaded_path["path"]
```

- [ ] **Step 4: Run test, verify passes** — `pytest tests/core/test_downloader.py -v` → 3 passed

- [ ] **Step 5: Commit** — `git add src/audioforge/core/downloader.py tests/core/test_downloader.py && git commit -m "feat: add yt-dlp probe() and download_audio()"`

---

### Task 3: Engine self-update (`update_ytdlp()`)

**Files:**
- Modify: `src/audioforge/core/downloader.py`
- Test: `tests/core/test_downloader.py` (append)

**Interfaces:**
- Produces: `update_ytdlp() -> str` (returns the new version string) — consumed by a Settings-dialog button in sub-plan 6.

- [ ] **Step 1: Write the failing test**

```python
# append to tests/core/test_downloader.py
from unittest.mock import patch
from audioforge.core.downloader import update_ytdlp


@patch("audioforge.core.downloader.subprocess.run")
def test_update_ytdlp_runs_pip_upgrade(mock_run):
    mock_run.return_value.returncode = 0
    mock_run.return_value.stdout = "Successfully installed yt-dlp-2024.9.1"

    result = update_ytdlp()

    args = mock_run.call_args[0][0]
    assert args[:4] == ["python", "-m", "pip", "install"]
    assert "--upgrade" in args
    assert "yt-dlp" in args
    assert "2024.9.1" in result
```

- [ ] **Step 2: Run test, verify fails** — `ImportError: cannot import name 'update_ytdlp'`

- [ ] **Step 3: Implement**

```python
# append to src/audioforge/core/downloader.py
import subprocess
import sys


def update_ytdlp() -> str:
    """Upgrade yt-dlp via pip. Returns pip's stdout (contains the new version)."""
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "--upgrade", "yt-dlp"],
        capture_output=True, text=True, check=False,
    )
    if result.returncode != 0:
        raise DownloadError(f"Failed to update yt-dlp: {result.stderr[-500:]}")
    return result.stdout
```

Note: test patches `audioforge.core.downloader.subprocess.run`, so `import subprocess` (not `from subprocess import run`) is required at module level.

- [ ] **Step 4: Run test, verify passes**

- [ ] **Step 5: Commit** — `git commit -am "feat: add in-app yt-dlp self-update"`
