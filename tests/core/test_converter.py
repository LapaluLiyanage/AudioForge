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
