from dataclasses import dataclass

SUPPORTED_FORMATS = {"wav", "flac", "mp3", "m4a", "opus"}


@dataclass(frozen=True)
class ConversionOptions:
    format: str
    sample_rate: int | None = 44100
    bit_depth: int | None = 16

    def __post_init__(self):
        if self.format not in SUPPORTED_FORMATS:
            raise ValueError(f"Unsupported format: {self.format!r}. Supported: {sorted(SUPPORTED_FORMATS)}")


@dataclass(frozen=True)
class ConversionResult:
    output_path: str
    skipped_reencode: bool = False


class ConversionError(Exception):
    """Raised when FFmpeg fails to convert a file."""


@dataclass(frozen=True)
class TrackMetadata:
    id: str
    title: str
    uploader: str
    duration_seconds: int
    url: str
    thumbnail_url: str | None = None


class DownloadError(Exception):
    """Raised when yt-dlp cannot probe or download a URL."""
