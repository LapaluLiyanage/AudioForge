"""yt-dlp wrapper: metadata probing and raw audio download."""
from __future__ import annotations

import subprocess
import sys
from collections.abc import Callable

import yt_dlp

from audioforge.core.models import DownloadError, TrackMetadata


def _to_metadata(info: dict) -> TrackMetadata:
    return TrackMetadata(
        id=info["id"],
        title=info.get("title", "Unknown title"),
        uploader=info.get("uploader", "Unknown"),
        duration_seconds=int(info.get("duration") or 0),
        url=info.get("webpage_url", info.get("url", "")),
        thumbnail_url=info.get("thumbnail"),
    )


def probe(url: str) -> TrackMetadata | list[TrackMetadata]:
    opts = {"quiet": True, "no_warnings": True, "extract_flat": "in_playlist", "skip_download": True}
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
    except yt_dlp.utils.DownloadError as exc:
        raise DownloadError(str(exc)) from exc

    if info is None:
        raise DownloadError(f"yt-dlp returned no information for {url}.")

    if info.get("_type") == "playlist":
        return [_to_metadata(entry) for entry in info["entries"] if entry and entry.get("id")]
    return _to_metadata(info)


def download_audio(
    url: str,
    dest_dir: str,
    on_progress: Callable[[float], None] | None = None,
) -> str:
    """Download the best available raw audio stream. Returns the downloaded file path."""
    downloaded_path: dict[str, str] = {}

    def _hook(status: dict) -> None:
        if status["status"] == "downloading" and on_progress:
            total = status.get("total_bytes") or status.get("total_bytes_estimate")
            if total:
                on_progress(status.get("downloaded_bytes", 0) / total * 100)
        elif status["status"] == "finished":
            downloaded_path["path"] = status["filename"]

    opts = {
        "quiet": True,
        "no_warnings": True,
        "format": "bestaudio/best",
        "outtmpl": f"{dest_dir}/%(id)s.%(ext)s",
        "progress_hooks": [_hook],
        "noplaylist": True,
    }
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([url])
    except yt_dlp.utils.DownloadError as exc:
        raise DownloadError(str(exc)) from exc

    if "path" not in downloaded_path:
        raise DownloadError("Download finished but no output file was reported by yt-dlp.")
    return downloaded_path["path"]


def update_ytdlp() -> str:
    """Upgrade yt-dlp via pip. Returns pip's stdout (contains the new version)."""
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "--upgrade", "yt-dlp"],
        capture_output=True, text=True, check=False,
    )
    if result.returncode != 0:
        raise DownloadError(f"Failed to update yt-dlp: {result.stderr[-500:]}")
    return result.stdout
