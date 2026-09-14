"""mutagen-based metadata tagging.

Dispatches by output format to the mutagen API appropriate for that
container:

- ``mp3``  -> ID3 tags via ``mutagen.easyid3.EasyID3``.
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
  write.
"""
from __future__ import annotations

from mutagen.easyid3 import EasyID3
from mutagen.flac import FLAC
from mutagen.mp4 import MP4
from mutagen.oggopus import OggOpus

from audioforge.core.models import TrackMetadata

_MP4_FREEFORM_COMMENT = "\xa9cmt"


def write_tags(file_path: str, metadata: TrackMetadata, format: str, download_date: str) -> None:
    if format == "wav":
        return  # no reliable universal WAV tagging support; documented limitation

    if format == "mp3":
        try:
            tags = EasyID3(file_path)
        except Exception:
            tags = EasyID3()
            tags.save(file_path)
            tags = EasyID3(file_path)
        tags["title"] = metadata.title
        tags["artist"] = metadata.uploader
        tags["comment"] = metadata.url
        tags["date"] = download_date
        tags.save()
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
    else:
        raise ValueError(f"Unsupported format for tagging: {format!r}")
