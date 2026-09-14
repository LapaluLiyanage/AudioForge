import struct
import wave

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


# Regression harness for C1 (invalid -sample_fmt s24), C2 (WAV bit depth must
# come from the codec, not -sample_fmt), and C3/C3-opus (FLAC 24-bit needs
# -bits_per_raw_sample; opus needs -ar omitted). Each of these combinations
# previously failed against a real ffmpeg install except wav/flac 16-bit.
@pytest.mark.parametrize(
    "fmt,sample_rate,bit_depth",
    [
        ("wav", 44100, 16),
        ("wav", 48000, 24),
        ("wav", 48000, 32),
        ("flac", 44100, 16),
        ("flac", 48000, 24),
        ("flac", 48000, 32),
        ("mp3", 44100, None),
        ("opus", None, None),
    ],
)
def test_convert_all_supported_format_combinations(tmp_path, fmt, sample_rate, bit_depth):
    src = tmp_path / "in.wav"
    dst = tmp_path / f"out.{fmt}"
    _make_silent_wav(src)

    result = convert(
        str(src), str(dst), ConversionOptions(format=fmt, sample_rate=sample_rate, bit_depth=bit_depth)
    )

    assert dst.exists()
    assert dst.stat().st_size > 0
    assert result.output_path == str(dst)
