import pytest
from audioforge.core.models import ConversionOptions, TrackMetadata

def test_conversion_options_rejects_unsupported_format():
    with pytest.raises(ValueError):
        ConversionOptions(format="wma", sample_rate=44100, bit_depth=16)

def test_conversion_options_accepts_supported_formats():
    for fmt in ("wav", "flac", "mp3", "m4a", "opus"):
        ConversionOptions(format=fmt, sample_rate=44100, bit_depth=16)

def test_track_metadata_holds_expected_fields():
    m = TrackMetadata(
        id="abc123", title="Song Title", uploader="Channel Name",
        duration_seconds=215, url="https://youtube.com/watch?v=abc123",
        thumbnail_url="https://img/thumb.jpg",
    )
    assert m.duration_seconds == 215
    assert m.title == "Song Title"
