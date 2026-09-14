import subprocess

import pytest

from audioforge.core.converter import build_ffmpeg_command, convert
from audioforge.core.models import ConversionError, ConversionOptions


def test_wav_command_selects_bit_depth_via_codec_not_sample_fmt():
    # C1/C2 regression: WAV bit depth must be selected via -c:a pcm_s24le,
    # not -sample_fmt s24 (not a valid ffmpeg sample format, and the WAV
    # muxer ignores -sample_fmt and always writes pcm_s16le anyway).
    opts = ConversionOptions(format="wav", sample_rate=48000, bit_depth=24)
    cmd = build_ffmpeg_command("ffmpeg", "in.webm", "out.wav", opts)
    assert cmd[0] == "ffmpeg"
    assert "-ar" in cmd and cmd[cmd.index("-ar") + 1] == "48000"
    assert "-c:a" in cmd and cmd[cmd.index("-c:a") + 1] == "pcm_s24le"
    assert "-sample_fmt" not in cmd
    assert cmd[-1] == "out.wav"


def test_wav_command_16bit_and_32bit_codecs():
    cmd16 = build_ffmpeg_command(
        "ffmpeg", "in.webm", "out.wav", ConversionOptions(format="wav", bit_depth=16)
    )
    assert cmd16[cmd16.index("-c:a") + 1] == "pcm_s16le"

    cmd32 = build_ffmpeg_command(
        "ffmpeg", "in.webm", "out.wav", ConversionOptions(format="wav", bit_depth=32)
    )
    assert cmd32[cmd32.index("-c:a") + 1] == "pcm_s32le"


def test_flac_24bit_uses_s32_sample_fmt_and_bits_per_raw_sample():
    # C3 regression: 24-bit FLAC needs -sample_fmt s32 -bits_per_raw_sample 24,
    # not a nonexistent s24 sample format.
    opts = ConversionOptions(format="flac", sample_rate=44100, bit_depth=24)
    cmd = build_ffmpeg_command("ffmpeg", "in.webm", "out.flac", opts)
    assert cmd[cmd.index("-sample_fmt") + 1] == "s32"
    assert "-bits_per_raw_sample" in cmd and cmd[cmd.index("-bits_per_raw_sample") + 1] == "24"


def test_flac_16bit_and_32bit_sample_fmt():
    cmd16 = build_ffmpeg_command(
        "ffmpeg", "in.webm", "out.flac", ConversionOptions(format="flac", bit_depth=16)
    )
    assert cmd16[cmd16.index("-sample_fmt") + 1] == "s16"
    assert "-bits_per_raw_sample" not in cmd16

    cmd32 = build_ffmpeg_command(
        "ffmpeg", "in.webm", "out.flac", ConversionOptions(format="flac", bit_depth=32)
    )
    assert cmd32[cmd32.index("-sample_fmt") + 1] == "s32"
    assert "-bits_per_raw_sample" not in cmd32


def test_mp3_command_uses_320k_bitrate():
    opts = ConversionOptions(format="mp3", sample_rate=44100, bit_depth=None)
    cmd = build_ffmpeg_command("ffmpeg", "in.webm", "out.mp3", opts)
    assert "-b:a" in cmd and cmd[cmd.index("-b:a") + 1] == "320k"


def test_opus_command_omits_explicit_sample_rate():
    # C3-opus regression: the default sample_rate (44100) is not one of
    # libopus's supported rates, so -ar must be omitted entirely for opus.
    opts = ConversionOptions(format="opus")
    cmd = build_ffmpeg_command("ffmpeg", "in.webm", "out.opus", opts)
    assert "-ar" not in cmd
    assert "-b:a" in cmd and cmd[cmd.index("-b:a") + 1] == "160k"


def test_command_always_overwrites_and_hides_banner():
    opts = ConversionOptions(format="flac", sample_rate=44100, bit_depth=16)
    cmd = build_ffmpeg_command("ffmpeg", "in.webm", "out.flac", opts)
    assert "-y" in cmd
    assert "-hide_banner" in cmd


class _FakeProcess:
    def __init__(self, returncode, stdout="", stderr=""):
        self.returncode = returncode
        self._stdout = stdout
        self._stderr = stderr
        self.killed = False

    def communicate(self, timeout=None):
        return self._stdout, self._stderr

    def kill(self):
        self.killed = True


def test_convert_raises_conversion_error_on_nonzero_returncode(monkeypatch):
    monkeypatch.setattr("audioforge.core.converter.find_ffmpeg", lambda: "ffmpeg")
    monkeypatch.setattr("audioforge.core.converter._probe_source", lambda *a, **k: None)
    monkeypatch.setattr(
        subprocess,
        "Popen",
        lambda *a, **k: _FakeProcess(returncode=1, stderr="some ffmpeg failure detail"),
    )

    with pytest.raises(ConversionError, match="some ffmpeg failure detail"):
        convert("in.webm", "out.wav", ConversionOptions(format="wav"))


def test_convert_raises_clear_error_when_ffmpeg_missing(monkeypatch):
    monkeypatch.setattr("audioforge.core.converter.find_ffmpeg", lambda: None)

    with pytest.raises(ConversionError, match="FFmpeg was not found"):
        convert("in.webm", "out.wav", ConversionOptions(format="wav"))


def test_convert_succeeds_and_returns_result_on_zero_returncode(monkeypatch):
    monkeypatch.setattr("audioforge.core.converter.find_ffmpeg", lambda: "ffmpeg")
    monkeypatch.setattr("audioforge.core.converter._probe_source", lambda *a, **k: None)
    monkeypatch.setattr(
        subprocess, "Popen", lambda *a, **k: _FakeProcess(returncode=0, stdout="ok")
    )

    result = convert("in.webm", "out.wav", ConversionOptions(format="wav"))
    assert result.output_path == "out.wav"
    assert result.skipped_reencode is False


def test_convert_times_out_and_kills_process(monkeypatch):
    class _HangingProcess(_FakeProcess):
        def __init__(self):
            super().__init__(returncode=None)

        def communicate(self, timeout=None):
            if not self.killed:
                raise subprocess.TimeoutExpired(cmd="ffmpeg", timeout=timeout)
            return "", ""

    monkeypatch.setattr("audioforge.core.converter.find_ffmpeg", lambda: "ffmpeg")
    monkeypatch.setattr("audioforge.core.converter._probe_source", lambda *a, **k: None)
    monkeypatch.setattr(subprocess, "Popen", lambda *a, **k: _HangingProcess())

    with pytest.raises(ConversionError, match="timed out"):
        convert("in.webm", "out.wav", ConversionOptions(format="wav"), timeout=0.01)


def test_convert_skips_reencode_when_source_already_matches(monkeypatch, tmp_path):
    src = tmp_path / "in.wav"
    dst = tmp_path / "out.wav"
    src.write_bytes(b"fake-wav-bytes")

    monkeypatch.setattr("audioforge.core.converter.find_ffmpeg", lambda: "ffmpeg")
    monkeypatch.setattr(
        "audioforge.core.converter._probe_source",
        lambda *a, **k: {"codec_name": "pcm_s16le", "sample_rate": 44100, "bit_depth": 16},
    )

    def _unexpected_popen(*args, **kwargs):
        raise AssertionError("ffmpeg should not be invoked when skipping re-encode")

    monkeypatch.setattr(subprocess, "Popen", _unexpected_popen)

    result = convert(
        str(src), str(dst), ConversionOptions(format="wav", sample_rate=44100, bit_depth=16)
    )

    assert result.skipped_reencode is True
    assert dst.read_bytes() == src.read_bytes()
