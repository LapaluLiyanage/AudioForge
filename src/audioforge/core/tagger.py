"""mutagen-based metadata tagging.

Dispatches by output format to the mutagen API appropriate for that
container:

- ``mp3``  -> ID3 tags via ``mutagen.easyid3.EasyID3`` for title/artist/date.
  ``EasyID3`` has no ``"comment"`` key (it only maps a fixed set of ID3 text
  frames), so the comment (source URL) is written as a raw ``COMM`` frame via
  ``mutagen.id3.ID3``/``mutagen.id3.COMM`` instead.
- ``flac`` -> Vorbis comments via ``mutagen.flac.FLAC``.
- ``m4a``  -> MP4 atoms via ``mutagen.mp4.MP4`` (``\\xa9nam``/``\\xa9ART``/
  ``\\xa9cmt``/``\\xa9day``).
- ``opus`` -> Vorbis comments via ``mutagen.oggopus.OggOpus``. Real ``.opus``
  output is an Ogg container, NOT an MP4 container, so it must NOT be routed
  through ``mutagen.mp4.MP4`` (that raises ``MP4StreamInfoError`` on a real
  Ogg Opus file). OggOpus uses the same Vorbis-comment-style keys as FLAC
  (``title``/``artist``/``comment``/``date``).
- ``wav``  -> no-op; there is no reliably universal WAV tagging story across
  players, so this is a documented limitation rather than an attempted tag
  write. The skip is logged (not raised, not printed) per the "skip tagging
  silently" plan constraint.

Any real failure while writing tags (mutagen errors, file I/O errors) is
raised as ``audioforge.core.models.TaggingError``. An unrecognized ``format``
string raises ``ValueError`` (a caller/programmer error, not a runtime tag
write failure).
"""
from __future__ import annotations

import logging

from mutagen import MutagenError
from mutagen.easyid3 import EasyID3
from mutagen.flac import FLAC
from mutagen.id3 import COMM, ID3
from mutagen.mp4 import MP4
from mutagen.oggopus import OggOpus

from audioforge.core.models import TaggingError, TrackMetadata

logger = logging.getLogger(__name__)

_MP4_FREEFORM_COMMENT = "\xa9cmt"
_TAGGABLE_FORMATS = {"mp3", "flac", "m4a", "opus"}


def write_tags(file_path: str, metadata: TrackMetadata, format: str, download_date: str) -> None:
    if format == "wav":
        logger.info(
            "Skipping tag write for %s: WAV has no reliable universal tagging "
            "support across players (documented limitation).",
            file_path,
        )
        return

    if format not in _TAGGABLE_FORMATS:
        raise ValueError(f"Unsupported format for tagging: {format!r}")

    try:
        if format == "mp3":
            _write_mp3_tags(file_path, metadata, download_date)
        elif format == "flac":
            tags = FLAC(file_path)
            tags["title"] = metadata.title
            tags["artist"] = metadata.uploader
            tags["comment"] = metadata.url
            tags["date"] = download_date
            tags.save()
        elif format == "m4a":
            tags = MP4(file_path)
            tags["\xa9nam"] = [metadata.title]
            tags["\xa9ART"] = [metadata.uploader]
            tags[_MP4_FREEFORM_COMMENT] = [metadata.url]
            tags["\xa9day"] = [download_date]
            tags.save()
        elif format == "opus":
            # Real .opus output is an Ogg container, not MP4 -- must use
            # OggOpus, never mutagen.mp4.MP4 (see module docstring).
            tags = OggOpus(file_path)
            tags["title"] = metadata.title
            tags["artist"] = metadata.uploader
            tags["comment"] = metadata.url
            tags["date"] = download_date
            tags.save()
    except (MutagenError, OSError) as exc:
        raise TaggingError(f"Failed to write tags to {file_path!r}: {exc}") from exc


def _write_mp3_tags(file_path: str, metadata: TrackMetadata, download_date: str) -> None:
    try:
        tags = EasyID3(file_path)
    except Exception:
        tags = EasyID3()
        tags.save(file_path)
        tags = EasyID3(file_path)
    tags["title"] = metadata.title
    tags["artist"] = metadata.uploader
    tags["date"] = download_date
    tags.save()

    # EasyID3 has no "comment" key -- it only maps a fixed set of ID3 text
    # frames and raises EasyID3KeyError for anything outside that set. Write
    # the source URL as a raw COMM frame via the low-level ID3 API instead.
    # Note: this does NOT read back through EasyID3 -- read it back via
    # mutagen.id3.ID3 (see tests/core/test_tagger.py::test_write_tags_mp3).
    id3 = ID3(file_path)
    id3.setall("COMM", [COMM(encoding=3, lang="eng", desc="", text=[metadata.url])])
    id3.save(file_path)
