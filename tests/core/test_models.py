import pytest
from audioforge.core.models import ConversionOptions

def test_conversion_options_rejects_unsupported_format():
    with pytest.raises(ValueError):
        ConversionOptions(format="wma", sample_rate=44100, bit_depth=16)

def test_conversion_options_accepts_supported_formats():
    for fmt in ("wav", "flac", "mp3", "m4a", "opus"):
        ConversionOptions(format=fmt, sample_rate=44100, bit_depth=16)
