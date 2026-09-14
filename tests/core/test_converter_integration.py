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
