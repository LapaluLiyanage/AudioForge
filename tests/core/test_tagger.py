import shutil
from pathlib import Path
from unittest.mock import patch

import pytest
from mutagen import MutagenError
from mutagen.flac import FLAC
from mutagen.id3 import ID3
from mutagen.mp4 import MP4
from mutagen.oggopus import OggOpus

from audioforge.core.models import TaggingError, TrackMetadata
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


def test_write_tags_mp3(tmp_path):
    dest = tmp_path / "track.mp3"
    shutil.copy(FIXTURES / "empty.mp3", dest)

    write_tags(str(dest), make_meta(), "mp3", download_date="2026-09-14")

    # EasyID3 has no "comment" key, so title/artist/date read back via
    # EasyID3, but the comment (URL) must be read back via the raw ID3 API,
    # which is what actually round-trips a COMM frame.
    from mutagen.easyid3 import EasyID3

    easy_tags = EasyID3(str(dest))
    assert easy_tags["title"][0] == "Test Track"
    assert easy_tags["artist"][0] == "Test Channel"
    assert easy_tags["date"][0] == "2026-09-14"

    id3 = ID3(str(dest))
    comments = id3.getall("COMM")
    assert len(comments) == 1
    assert comments[0].text[0] == "https://youtube.com/watch?v=abc123"


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


def test_write_tags_wav_is_noop_logs_skip(tmp_path, caplog):
    dest = tmp_path / "track.wav"
    dest.write_bytes(b"RIFF....WAVEfmt ")

    with caplog.at_level("INFO", logger="audioforge.core.tagger"):
        write_tags(str(dest), make_meta(), "wav", download_date="2026-09-14")

    assert any("wav" in record.message.lower() for record in caplog.records)


def test_write_tags_wraps_mutagen_errors_in_tagging_error(tmp_path):
    dest = tmp_path / "track.flac"
    shutil.copy(FIXTURES / "empty.flac", dest)

    with patch("audioforge.core.tagger.FLAC", side_effect=MutagenError("boom")):
        with pytest.raises(TaggingError):
            write_tags(str(dest), make_meta(), "flac", download_date="2026-09-14")


def test_write_tags_unsupported_format_raises_value_error(tmp_path):
    dest = tmp_path / "track.xyz"
    dest.write_bytes(b"x")

    with pytest.raises(ValueError):
        write_tags(str(dest), make_meta(), "xyz", download_date="2026-09-14")
