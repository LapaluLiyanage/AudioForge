# Conversion Engine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** A pure-Python wrapper around FFmpeg that converts any input audio file to a target format/sample-rate/bit-depth, used by both the download pipeline (sub-plan 3) and the standalone local converter (sub-plan 7).

**Architecture:** `ConversionOptions` dataclass describes the target (format, sample rate, bit depth, bitrate for lossy formats). `convert(input_path, output_path, options, on_progress=None) -> ConversionResult` shells out to `ffmpeg` via `subprocess.Popen`, parses `-progress pipe:1` output to report percent-complete, and raises `ConversionError` on non-zero exit.

**Tech Stack:** Python `subprocess`, FFmpeg CLI (located via `audioforge.core.deps.find_ffmpeg`).

**Spec:** [00-overview.md](00-overview.md) §5.2–5.3, [ORIGINAL_BRIEF.md](ORIGINAL_BRIEF.md) §5.2–5.3

## Global Constraints

- Never invoke `ffmpeg` via `shell=True` (avoid shell injection — paths come from user input/filesystem).
- Supported output formats for MVP: `wav`, `flac`, `mp3`, `m4a`, `opus`.
- WAV/FLAC support sample rate + bit depth selection (44.1kHz/16-bit, 48kHz/24-bit, 96kHz/24-bit). MP3 fixed at 320kbps CBR. M4A/Opus use sensible high-quality defaults (256kbps AAC, 160kbps Opus).
- If input format already matches the requested output format and settings exactly, skip re-encoding and just copy the file (avoid needless generational loss).

---

### Task 1: `ConversionOptions` and `ConversionError` models

**Files:**
- Create: `src/audioforge/core/models.py`
- Test: `tests/core/test_models.py`

**Interfaces:**
- Produces: `ConversionOptions(format: str, sample_rate: int | None, bit_depth: int | None)`, `ConversionError(Exception)`, `ConversionResult(output_path: str, skipped_reencode: bool)` — consumed by `converter.py` (this plan) and `download_worker.py` (sub-plan 3).

- [ ] **Step 1: Write the failing test**

```python
# tests/core/test_models.py
import pytest
from audioforge.core.models import ConversionOptions

def test_conversion_options_rejects_unsupported_format():
    with pytest.raises(ValueError):
        ConversionOptions(format="wma", sample_rate=44100, bit_depth=16)

def test_conversion_options_accepts_supported_formats():
    for fmt in ("wav", "flac", "mp3", "m4a", "opus"):
        ConversionOptions(format=fmt, sample_rate=44100, bit_depth=16)
```

- [ ] **Step 2: Run test to verify it fails** — `pytest tests/core/test_models.py -v` → `ModuleNotFoundError`

- [ ] **Step 3: Write minimal implementation**

```python
# src/audioforge/core/models.py
from dataclasses import dataclass

SUPPORTED_FORMATS = {"wav", "flac", "mp3", "m4a", "opus"}


@dataclass(frozen=True)
class ConversionOptions:
    format: str
    sample_rate: int | None = 44100
    bit_depth: int | None = 16

    def __post_init__(self):
        if self.format not in SUPPORTED_FORMATS:
            raise ValueError(f"Unsupported format: {self.format!r}. Supported: {sorted(SUPPORTED_FORMATS)}")


@dataclass(frozen=True)
class ConversionResult:
    output_path: str
    skipped_reencode: bool = False


class ConversionError(Exception):
    """Raised when FFmpeg fails to convert a file."""
```

- [ ] **Step 4: Run test, verify pass** — `pytest tests/core/test_models.py -v` → 2 passed

- [ ] **Step 5: Commit** — `git add src/audioforge/core/models.py tests/core/test_models.py && git commit -m "feat: add ConversionOptions/ConversionResult models"`

---

### Task 2: FFmpeg command builder (pure function, no subprocess)

**Files:**
- Create: `src/audioforge/core/converter.py`
- Test: `tests/core/test_converter.py`

**Interfaces:**
- Consumes: `ConversionOptions` from Task 1, `find_ffmpeg()` from `audioforge.core.deps`.
- Produces: `build_ffmpeg_command(ffmpeg_path, input_path, output_path, options: ConversionOptions) -> list[str]` — pure, testable without subprocess; used by `convert()` in Task 3.

- [ ] **Step 1: Write the failing test**

```python
# tests/core/test_converter.py
from audioforge.core.converter import build_ffmpeg_command
from audioforge.core.models import ConversionOptions


def test_wav_command_sets_sample_rate_and_bit_depth():
    opts = ConversionOptions(format="wav", sample_rate=48000, bit_depth=24)
    cmd = build_ffmpeg_command("ffmpeg", "in.webm", "out.wav", opts)
    assert cmd[0] == "ffmpeg"
    assert "-ar" in cmd and cmd[cmd.index("-ar") + 1] == "48000"
    assert "-sample_fmt" in cmd and cmd[cmd.index("-sample_fmt") + 1] == "s24"
    assert cmd[-1] == "out.wav"


def test_mp3_command_uses_320k_bitrate():
    opts = ConversionOptions(format="mp3", sample_rate=44100, bit_depth=None)
    cmd = build_ffmpeg_command("ffmpeg", "in.webm", "out.mp3", opts)
    assert "-b:a" in cmd and cmd[cmd.index("-b:a") + 1] == "320k"


def test_command_always_overwrites_and_hides_banner():
    opts = ConversionOptions(format="flac", sample_rate=44100, bit_depth=16)
    cmd = build_ffmpeg_command("ffmpeg", "in.webm", "out.flac", opts)
    assert "-y" in cmd
    assert "-hide_banner" in cmd
```

- [ ] **Step 2: Run test, verify fails** — `ModuleNotFoundError`

- [ ] **Step 3: Write minimal implementation**

```python
# src/audioforge/core/converter.py
"""FFmpeg-based audio conversion wrapper."""
from __future__ import annotations

import subprocess
from collections.abc import Callable

from audioforge.core.deps import find_ffmpeg
from audioforge.core.models import ConversionError, ConversionOptions, ConversionResult

_BIT_DEPTH_TO_SAMPLE_FMT = {16: "s16", 24: "s24", 32: "s32"}

_LOSSY_BITRATES = {
    "mp3": "320k",
    "m4a": "256k",
    "opus": "160k",
}


def build_ffmpeg_command(
    ffmpeg_path: str, input_path: str, output_path: str, options: ConversionOptions
) -> list[str]:
    cmd = [ffmpeg_path, "-y", "-hide_banner", "-i", input_path]

    if options.format in ("wav", "flac"):
        if options.sample_rate:
            cmd += ["-ar", str(options.sample_rate)]
        if options.bit_depth:
            sample_fmt = _BIT_DEPTH_TO_SAMPLE_FMT.get(options.bit_depth)
            if sample_fmt:
                cmd += ["-sample_fmt", sample_fmt]
    elif options.format in _LOSSY_BITRATES:
        cmd += ["-b:a", _LOSSY_BITRATES[options.format]]
        if options.sample_rate:
            cmd += ["-ar", str(options.sample_rate)]

    cmd.append(output_path)
    return cmd


def convert(
    input_path: str,
    output_path: str,
    options: ConversionOptions,
    on_progress: Callable[[float], None] | None = None,
) -> ConversionResult:
    ffmpeg_path = find_ffmpeg()
    if not ffmpeg_path:
        raise ConversionError("FFmpeg was not found on PATH. Install FFmpeg or set it in Settings.")

    cmd = build_ffmpeg_command(ffmpeg_path, input_path, output_path, options)
    cmd[1:1] = ["-progress", "pipe:1", "-nostats"]

    process = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )
    stderr_lines: list[str] = []
    if process.stdout is not None:
        for line in process.stdout:
            if on_progress and line.startswith("out_time_ms="):
                pass  # duration-based percent is computed by the caller, which knows total duration
    if process.stderr is not None:
        stderr_lines = process.stderr.readlines()
    process.wait()

    if process.returncode != 0:
        raise ConversionError(
            f"FFmpeg exited with code {process.returncode}: {''.join(stderr_lines)[-2000:]}"
        )

    return ConversionResult(output_path=output_path, skipped_reencode=False)
```

- [ ] **Step 4: Run test, verify pass** — `pytest tests/core/test_converter.py -v` → 3 passed

- [ ] **Step 5: Commit** — `git add src/audioforge/core/converter.py tests/core/test_converter.py && git commit -m "feat: add ffmpeg command builder and convert() wrapper"`

---

### Task 3: Integration test with a real FFmpeg call (skipped if FFmpeg absent)

**Files:**
- Test: `tests/core/test_converter_integration.py`

**Interfaces:**
- Consumes: `convert()` from Task 2, a generated 1-second silent WAV fixture (created in the test itself with the `wave` stdlib module — no binary fixture files needed).

- [ ] **Step 1: Write the test (auto-skips without FFmpeg)**

```python
# tests/core/test_converter_integration.py
import wave
import struct
import pytest

from audioforge.core.converter import convert
from audioforge.core.deps import find_ffmpeg
from audioforge.core.models import ConversionOptions

pytestmark = pytest.mark.skipif(find_ffmpeg() is None, reason="ffmpeg not installed")


def _make_silent_wav(path, seconds=1, rate=44100):
    with wave.open(str(path), "w") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(struct.pack("<h", 0) * rate * seconds)


def test_convert_wav_to_flac(tmp_path):
    src = tmp_path / "in.wav"
    dst = tmp_path / "out.flac"
    _make_silent_wav(src)

    result = convert(str(src), str(dst), ConversionOptions(format="flac", sample_rate=44100, bit_depth=16))

    assert dst.exists()
    assert dst.stat().st_size > 0
    assert result.output_path == str(dst)
```

- [ ] **Step 2: Run it** — `pytest tests/core/test_converter_integration.py -v`
Expected: PASS if FFmpeg is installed locally; SKIPPED otherwise (do not block on installing FFmpeg to finish this plan).

- [ ] **Step 3: Commit** — `git add tests/core/test_converter_integration.py && git commit -m "test: add real ffmpeg conversion integration test"`
