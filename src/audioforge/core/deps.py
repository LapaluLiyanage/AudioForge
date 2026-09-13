"""Runtime checks for external dependencies (FFmpeg binary, yt-dlp import)."""
import shutil


def find_ffmpeg() -> str | None:
    return shutil.which("ffmpeg")


def check_dependencies() -> dict[str, bool]:
    try:
        import yt_dlp  # noqa: F401
        ytdlp_ok = True
    except ImportError:
        ytdlp_ok = False
    return {
        "ffmpeg": find_ffmpeg() is not None,
        "yt_dlp": ytdlp_ok,
    }
