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
    # Use communicate() to read stdout/stderr concurrently rather than draining
    # one pipe fully before the other. FFmpeg writes both streams at the same
    # time; reading them sequentially can deadlock once the OS pipe buffer for
    # the unread stream fills up (most likely exactly when ffmpeg is emitting
    # a lot of stderr output, e.g. on a failing conversion).
    # TODO: on_progress is not yet wired to real progress — duration-based
    # percent will be computed by the caller in a later task.
    stdout, stderr = process.communicate()

    if process.returncode != 0:
        raise ConversionError(
            f"FFmpeg exited with code {process.returncode}: {stderr[-2000:]}"
        )

    return ConversionResult(output_path=output_path, skipped_reencode=False)
