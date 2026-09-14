import shutil
from pathlib import Path

import pytest
from mutagen.flac import FLAC
from mutagen.mp4 import MP4
from mutagen.oggopus import OggOpus

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


def test_write_tags_opus(tmp_path):
    dest = tmp_path / "track.opus"
    shutil.copy(FIXTURES / "empty.opus", dest)

    write_tags(str(dest), make_meta(), "opus", download_date="2026-09-14")

    tags = OggOpus(str(dest))
    assert tags["title"][0] == "Test Track"
    assert tags["artist"][0] == "Test Channel"
    assert tags["comment"][0] == "https://youtube.com/watch?v=abc123"


def test_write_tags_m4a(tmp_path):
    dest = tmp_path / "track.m4a"
    shutil.copy(FIXTURES / "empty.m4a", dest)

    write_tags(str(dest), make_meta(), "m4a", download_date="2026-09-14")

    tags = MP4(str(dest))
    assert tags["\xa9nam"][0] == "Test Track"
    assert tags["\xa9ART"][0] == "Test Channel"
    assert tags["\xa9cmt"][0] == "https://youtube.com/watch?v=abc123"


def test_write_tags_wav_is_noop(tmp_path):
    dest = tmp_path / "track.wav"
    dest.write_bytes(b"RIFF....WAVEfmt ")

    write_tags(str(dest), make_meta(), "wav", download_date="2026-09-14")  # must not raise


def test_write_tags_opus_never_routes_through_mp4(tmp_path):
    """Regression guard: opus must not be handled by mutagen.mp4.MP4,
    which raises on real Ogg-container .opus files."""
    dest = tmp_path / "track.opus"
    shutil.copy(FIXTURES / "empty.opus", dest)

    with pytest.raises(Exception):
        MP4(str(dest))
