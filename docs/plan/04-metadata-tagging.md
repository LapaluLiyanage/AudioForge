# Metadata Tagging & Output Organization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** After a file is converted (sub-plan 2), write ID3/Vorbis/MP4 tags (title, artist, source URL, download date) and place it at the correct organized output path.

**Architecture:** `tagger.write_tags(file_path, metadata: TrackMetadata, format: str)` dispatches to format-specific mutagen classes (`EasyID3` for mp3, `FLAC`, `MP4`, `WAVE` via `mutagen.wave` note below). `organizer.resolve_output_path(base_dir, project_name, metadata, format) -> str` builds `<base_dir>/<project_name>/<sanitized_title>.<ext>`, sanitizing filesystem-illegal characters and de-duplicating collisions with a numeric suffix.

**Tech Stack:** `mutagen` (`mutagen.easyid3`, `mutagen.flac`, `mutagen.mp4`).

**Spec:** [00-overview.md](00-overview.md) §5.5–5.6, [ORIGINAL_BRIEF.md](ORIGINAL_BRIEF.md) §5.5–5.6

## Global Constraints

- WAV has no standard universal tagging support in mutagen with the same reliability as ID3/FLAC/MP4 — for `wav` output, skip tagging silently (log, don't error) rather than corrupt the file. Document this limitation in the UI.
- Filenames must strip characters illegal on Windows (`<>:"/\|?*`) and trim to 200 chars.
- Never overwrite an existing file silently — if the resolved path exists, append ` (2)`, ` (3)`, etc.

---

### Task 1: `organizer.py` — output path resolution

**Files:**
- Create: `src/audioforge/core/organizer.py`
- Test: `tests/core/test_organizer.py`

**Interfaces:**
- Consumes: `TrackMetadata` from sub-plan 3.
- Produces: `sanitize_filename(name: str) -> str`, `resolve_output_path(base_dir: str, project_name: str, metadata: TrackMetadata, format: str) -> str` — consumed by `download_worker.py` (workers layer) to decide where the converter should write its output.

- [ ] **Step 1: Write the failing test**

```python
# tests/core/test_organizer.py
from audioforge.core.models import TrackMetadata
from audioforge.core.organizer import resolve_output_path, sanitize_filename


def make_meta(title="My Song: Remix?"):
    return TrackMetadata(id="1", title=title, uploader="Ch", duration_seconds=1, url="u")


def test_sanitize_filename_strips_illegal_characters():
    assert sanitize_filename('My Song: Remix?/\\<>') == "My Song Remix"


def test_resolve_output_path_builds_project_subfolder(tmp_path):
    path = resolve_output_path(str(tmp_path), "ClientA", make_meta("Track One"), "wav")
    assert path == str(tmp_path / "ClientA" / "Track One.wav")


def test_resolve_output_path_dedupes_existing_file(tmp_path):
    (tmp_path / "ClientA").mkdir()
    (tmp_path / "ClientA" / "Track One.wav").write_bytes(b"x")

    path = resolve_output_path(str(tmp_path), "ClientA", make_meta("Track One"), "wav")

    assert path == str(tmp_path / "ClientA" / "Track One (2).wav")
```

- [ ] **Step 2: Run test, verify fails** — `ModuleNotFoundError`

- [ ] **Step 3: Implement**

```python
# src/audioforge/core/organizer.py
"""Output filename sanitization and folder organization."""
from __future__ import annotations

import os
import re

from audioforge.core.models import TrackMetadata

_ILLEGAL_CHARS = re.compile(r'[<>:"/\\|?*]')


def sanitize_filename(name: str) -> str:
    cleaned = _ILLEGAL_CHARS.sub("", name)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned[:200] or "untitled"


def resolve_output_path(base_dir: str, project_name: str, metadata: TrackMetadata, format: str) -> str:
    folder = os.path.join(base_dir, sanitize_filename(project_name))
    stem = sanitize_filename(metadata.title)
    candidate = os.path.join(folder, f"{stem}.{format}")

    counter = 2
    while os.path.exists(candidate):
        candidate = os.path.join(folder, f"{stem} ({counter}).{format}")
        counter += 1
    return candidate
```

- [ ] **Step 4: Run test, verify passes** — 3 passed

- [ ] **Step 5: Commit** — `git add src/audioforge/core/organizer.py tests/core/test_organizer.py && git commit -m "feat: add output path organizer with collision-safe naming"`

---

### Task 2: `tagger.py` — write ID3/FLAC/MP4 tags

**Files:**
- Create: `src/audioforge/core/tagger.py`
- Test: `tests/core/test_tagger.py`

**Interfaces:**
- Consumes: `TrackMetadata` from sub-plan 3.
- Produces: `write_tags(file_path: str, metadata: TrackMetadata, format: str, download_date: str) -> None` — consumed by `download_worker.py` after conversion.

- [ ] **Step 1: Write the failing test**

Uses real small fixture files generated at test time (FFmpeg not required — mutagen can create tags on a minimal valid container the test builds with mutagen's own `save()` on an empty file for FLAC, or by using `mutagen.mp3.MP3` on a tiny valid MP3 header). To keep this dependency-free, test against FLAC and MP4 only (mutagen ships helpers to initialize empty valid files), and verify WAV is a no-op.

```python
# tests/core/test_tagger.py
import shutil
from pathlib import Path

import pytest
from mutagen.flac import FLAC

from audioforge.core.models import TrackMetadata
from audioforge.core.tagger import write_tags

FIXTURES = Path(__file__).parent / "fixtures"


def make_meta():
    return TrackMetadata(
        id="abc123", title="Test Track", uploader="Test Channel",
        duration_seconds=10, url="https://youtube.com/watch?v=abc123",
    )


def test_write_tags_flac(tmp_path):
    dest = tmp_path / "track.flac"
    shutil.copy(FIXTURES / "empty.flac", dest)

    write_tags(str(dest), make_meta(), "flac", download_date="2026-09-14")

    tags = FLAC(str(dest))
    assert tags["title"][0] == "Test Track"
    assert tags["artist"][0] == "Test Channel"
    assert tags["comment"][0] == "https://youtube.com/watch?v=abc123"


def test_write_tags_wav_is_noop(tmp_path):
    dest = tmp_path / "track.wav"
    dest.write_bytes(b"RIFF....WAVEfmt ")

    write_tags(str(dest), make_meta(), "wav", download_date="2026-09-14")  # must not raise
```

- [ ] **Step 2: Create the FLAC fixture** (one-time setup, not a test step but required before Step 3 can pass)

Run this once to generate `tests/core/fixtures/empty.flac` (requires FFmpeg; if unavailable, generate with the `flac` reference encoder, or hand-craft via `mutagen.flac.FLAC()` on a minimal valid FLAC produced by any available encoder in dev environment):

```powershell
mkdir tests\core\fixtures
ffmpeg -f lavfi -i anullsrc=r=44100:cl=mono -t 1 tests\core\fixtures\empty.flac
```

Commit this fixture binary to the repo (`git add tests/core/fixtures/empty.flac`).

- [ ] **Step 3: Run test to verify it fails** — `ModuleNotFoundError: No module named 'audioforge.core.tagger'`

- [ ] **Step 4: Implement**

```python
# src/audioforge/core/tagger.py
"""mutagen-based metadata tagging."""
from __future__ import annotations

from mutagen.easyid3 import EasyID3
from mutagen.flac import FLAC
from mutagen.mp4 import MP4

from audioforge.core.models import TrackMetadata

_MP4_FREEFORM_COMMENT = "\xa9cmt"


def write_tags(file_path: str, metadata: TrackMetadata, format: str, download_date: str) -> None:
    if format == "wav":
        return  # no reliable universal WAV tagging support; documented limitation

    if format == "mp3":
        try:
            tags = EasyID3(file_path)
        except Exception:
            tags = EasyID3()
            tags.save(file_path)
            tags = EasyID3(file_path)
        tags["title"] = metadata.title
        tags["artist"] = metadata.uploader
        tags["comment"] = metadata.url
        tags["date"] = download_date
        tags.save()
    elif format == "flac":
        tags = FLAC(file_path)
        tags["title"] = metadata.title
        tags["artist"] = metadata.uploader
        tags["comment"] = metadata.url
        tags["date"] = download_date
        tags.save()
    elif format in ("m4a", "opus"):
        tags = MP4(file_path)
        tags["\xa9nam"] = [metadata.title]
        tags["\xa9ART"] = [metadata.uploader]
        tags[_MP4_FREEFORM_COMMENT] = [metadata.url]
        tags["\xa9day"] = [download_date]
        tags.save()
```

- [ ] **Step 5: Run test, verify passes** — 2 passed

- [ ] **Step 6: Commit** — `git add src/audioforge/core/tagger.py tests/core/test_tagger.py tests/core/fixtures/empty.flac && git commit -m "feat: add mutagen tagging for flac/mp3/m4a/opus"`

Note: `opus` files are actually an Ogg container, not MP4 — `MP4()` will fail on real `.opus` output. Flag this as a known gap to fix during Task 2 code review: real opus tagging needs `mutagen.oggopus.OggOpus`, not `mutagen.mp4.MP4`. Fix before shipping MVP:

```python
    elif format == "opus":
        from mutagen.oggopus import OggOpus
        tags = OggOpus(file_path)
        tags["title"] = metadata.title
        tags["artist"] = metadata.uploader
        tags["comment"] = metadata.url
        tags["date"] = download_date
        tags.save()
    elif format == "m4a":
        tags = MP4(file_path)
        tags["\xa9nam"] = [metadata.title]
        tags["\xa9ART"] = [metadata.uploader]
        tags[_MP4_FREEFORM_COMMENT] = [metadata.url]
        tags["\xa9day"] = [download_date]
        tags.save()
```

Update the test file to add an `OggOpus` fixture/case symmetric to the FLAC one before considering this task done.
