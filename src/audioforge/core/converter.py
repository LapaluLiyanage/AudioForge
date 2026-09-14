"""FFmpeg-based audio conversion wrapper."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from collections.abc import Callable

from audioforge.core.deps import find_ffmpeg
from audioforge.core.models import ConversionError, ConversionOptions, ConversionResult

# WAV bit depth is selected via the codec (the muxer ignores -sample_fmt and
# always writes pcm_s16le otherwise).
_WAV_CODEC_BY_BIT_DEPTH = {16: "pcm_s16le", 24: "pcm_s24le", 32: "pcm_s32le"}

# FLAC bit depth is selected via -sample_fmt. There is no s24 sample format in
# ffmpeg; 24-bit FLAC uses the s32 sample format plus -bits_per_raw_sample 24
# to tell the encoder to only store 24 significant bits.
_FLAC_SAMPLE_FMT_BY_BIT_DEPTH = {16: "s16", 24: "s32", 32: "s32"}

_LOSSY_BITRATES = {
    "mp3": "320k",
    "m4a": "256k",
    "opus": "160k",
}

# libopus only supports these sample rates; requesting any other rate causes
# ffmpeg to fail outright, so -ar is omitted for opus and libopus picks its
# own default instead of clamping/mapping an unsupported rate.
_OPUS_NO_EXPLICIT_SAMPLE_RATE = {"opus"}

_DEFAULT_TIMEOUT_SECONDS = 600


def build_ffmpeg_command(
    ffmpeg_path: str, input_path: str, output_path: str, options: ConversionOptions
) -> list[str]:
    cmd = [ffmpeg_path, "-y", "-hide_banner", "-i", input_path]

    if options.format == "wav":
        if options.sample_rate:
            cmd += ["-ar", str(options.sample_rate)]
        if options.bit_depth:
            codec = _WAV_CODEC_BY_BIT_DEPTH.get(options.bit_depth)
            if codec:
                cmd += ["-c:a", codec]
    elif options.format == "flac":
        if options.sample_rate:
            cmd += ["-ar", str(options.sample_rate)]
        if options.bit_depth:
            sample_fmt = _FLAC_SAMPLE_FMT_BY_BIT_DEPTH.get(options.bit_depth)
            if sample_fmt:
                cmd += ["-sample_fmt", sample_fmt]
                if options.bit_depth == 24:
                    cmd += ["-bits_per_raw_sample", "24"]
    elif options.format in _LOSSY_BITRATES:
        cmd += ["-b:a", _LOSSY_BITRATES[options.format]]
        if options.sample_rate and options.format not in _OPUS_NO_EXPLICIT_SAMPLE_RATE:
            cmd += ["-ar", str(options.sample_rate)]

    cmd.append(output_path)
    return cmd


def _find_ffprobe(ffmpeg_path: str) -> str | None:
    """Locate ffprobe: prefer PATH, fall back to ffmpeg's own directory."""
    ffprobe = shutil.which("ffprobe")
    if ffprobe:
        return ffprobe
    ffmpeg_dir = os.path.dirname(ffmpeg_path)
    candidate_name = "ffprobe.exe" if os.name == "nt" else "ffprobe"
    candidate = os.path.join(ffmpeg_dir, candidate_name)
    if os.path.isfile(candidate):
        return candidate
    return None


def _probe_source(ffmpeg_path: str, input_path: str) -> dict | None:
    """Probe the source file's audio codec, sample rate, and bit depth.

    Returns None (never raises) if ffprobe is unavailable or probing fails
    for any reason -- callers must treat that as "unknown, do not skip
    re-encoding".
    """
    ffprobe_path = _find_ffprobe(ffmpeg_path)
    if not ffprobe_path:
        return None

    try:
        proc = subprocess.run(
            [
                ffprobe_path,
                "-v", "quiet",
                "-print_format", "json",
                "-show_streams",
                "-show_format",
                input_path,
            ],
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None

    if proc.returncode != 0:
        return None

    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return None

    audio_stream = next(
        (s for s in data.get("streams", []) if s.get("codec_type") == "audio"), None
    )
    if audio_stream is None:
        return None

    sample_rate = audio_stream.get("sample_rate")
    bit_depth = audio_stream.get("bits_per_raw_sample") or audio_stream.get("bits_per_sample")

    return {
        "codec_name": audio_stream.get("codec_name"),
        "sample_rate": int(sample_rate) if sample_rate else None,
        "bit_depth": int(bit_depth) if bit_depth else None,
    }


def _matches_options(probe: dict, options: ConversionOptions) -> bool:
    """Return True if the probed source already matches the requested output
    format/sample-rate/bit-depth exactly, i.e. re-encoding would be a no-op."""
    codec_name = probe.get("codec_name")

    if options.format == "wav":
        if codec_name not in _WAV_CODEC_BY_BIT_DEPTH.values():
            return False
        if options.bit_depth and _WAV_CODEC_BY_BIT_DEPTH.get(options.bit_depth) != codec_name:
            return False
    elif options.format == "flac":
        if codec_name != "flac":
            return False
        if options.bit_depth and probe.get("bit_depth") != options.bit_depth:
            return False
    elif options.format == "mp3":
        if codec_name != "mp3":
            return False
    elif options.format == "m4a":
        if codec_name != "aac":
            return False
    elif options.format == "opus":
        if codec_name != "opus":
            return False
    else:
        return False

    if options.sample_rate and probe.get("sample_rate") != options.sample_rate:
        return False

    return True


def convert(
    input_path: str,
    output_path: str,
    options: ConversionOptions,
    on_progress: Callable[[float], None] | None = None,
    timeout: float = _DEFAULT_TIMEOUT_SECONDS,
) -> ConversionResult:
    ffmpeg_path = find_ffmpeg()
    if not ffmpeg_path:
        raise ConversionError("FFmpeg was not found on PATH. Install FFmpeg or set it in Settings.")

    # Global constraint: if the source already matches the requested output
    # format/sample-rate/bit-depth exactly, skip re-encoding and just copy it.
    probe = _probe_source(ffmpeg_path, input_path)
    if probe is not None and _matches_options(probe, options):
        shutil.copyfile(input_path, output_path)
        return ConversionResult(output_path=output_path, skipped_reencode=True)

    cmd = build_ffmpeg_command(ffmpeg_path, input_path, output_path, options)
    cmd[1:1] = ["-progress", "pipe:1", "-nostats"]

    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        encoding="utf-8",
        errors="replace",
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
    )
    # Use communicate() to read stdout/stderr concurrently rather than draining
    # one pipe fully before the other. FFmpeg writes both streams at the same
    # time; reading them sequentially can deadlock once the OS pipe buffer for
    # the unread stream fills up (most likely exactly when ffmpeg is emitting
    # a lot of stderr output, e.g. on a failing conversion).
    # TODO: on_progress is not yet wired to real progress — duration-based
    # percent will be computed by the caller in a later task.
    try:
        stdout, stderr = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        process.kill()
        process.communicate()
        raise ConversionError(f"FFmpeg conversion timed out after {timeout}s.")

    if process.returncode != 0:
        raise ConversionError(
            f"FFmpeg exited with code {process.returncode}: {stderr[-2000:]}"
        )

    return ConversionResult(output_path=output_path, skipped_reencode=False)
