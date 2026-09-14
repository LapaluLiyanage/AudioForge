from unittest.mock import MagicMock, patch

import pytest

from audioforge.core.downloader import download_audio, probe
from audioforge.core.models import DownloadError, TrackMetadata

SINGLE_INFO = {
    "id": "abc123", "title": "Song Title", "uploader": "Channel",
    "duration": 215, "webpage_url": "https://youtube.com/watch?v=abc123",
    "thumbnail": "https://img/thumb.jpg",
}

PLAYLIST_INFO = {
    "_type": "playlist",
    "entries": [SINGLE_INFO, {**SINGLE_INFO, "id": "def456", "title": "Song 2"}],
}


@patch("audioforge.core.downloader.yt_dlp.YoutubeDL")
def test_probe_single_video_returns_one_metadata(mock_ydl_cls):
    mock_ydl = MagicMock()
    mock_ydl.extract_info.return_value = SINGLE_INFO
    mock_ydl_cls.return_value.__enter__.return_value = mock_ydl

    result = probe("https://youtube.com/watch?v=abc123")

    assert isinstance(result, TrackMetadata)
    assert result.id == "abc123"
    assert result.duration_seconds == 215


@patch("audioforge.core.downloader.yt_dlp.YoutubeDL")
def test_probe_playlist_returns_list(mock_ydl_cls):
    mock_ydl = MagicMock()
    mock_ydl.extract_info.return_value = PLAYLIST_INFO
    mock_ydl_cls.return_value.__enter__.return_value = mock_ydl

    result = probe("https://youtube.com/playlist?list=xyz")

    assert isinstance(result, list)
    assert len(result) == 2
    assert result[1].title == "Song 2"


@patch("audioforge.core.downloader.yt_dlp.YoutubeDL")
def test_probe_raises_download_error_on_extractor_failure(mock_ydl_cls):
    import yt_dlp
    mock_ydl = MagicMock()
    mock_ydl.extract_info.side_effect = yt_dlp.utils.DownloadError("Video unavailable")
    mock_ydl_cls.return_value.__enter__.return_value = mock_ydl

    with pytest.raises(DownloadError):
        probe("https://youtube.com/watch?v=deadbeef")


def _get_hook(mock_ydl_cls) -> callable:
    """Extract the real `_hook` closure passed as opts["progress_hooks"][0]."""
    args, kwargs = mock_ydl_cls.call_args
    opts = kwargs["opts"] if "opts" in kwargs else args[0]
    return opts["progress_hooks"][0]


@patch("audioforge.core.downloader.yt_dlp.YoutubeDL")
def test_download_audio_progress_hook_computes_percentage(mock_ydl_cls):
    mock_ydl = MagicMock()
    mock_ydl_cls.return_value.__enter__.return_value = mock_ydl

    on_progress = MagicMock()

    def fake_download(urls):
        hook = _get_hook(mock_ydl_cls)
        hook({"status": "downloading", "downloaded_bytes": 50, "total_bytes": 100})
        hook({"status": "finished", "filename": "/tmp/some/path.webm"})

    mock_ydl.download.side_effect = fake_download

    download_audio("https://youtube.com/watch?v=abc123", "/tmp/some", on_progress=on_progress)

    on_progress.assert_called_once_with(50.0)


@patch("audioforge.core.downloader.yt_dlp.YoutubeDL")
def test_download_audio_progress_hook_uses_total_bytes_estimate_fallback(mock_ydl_cls):
    mock_ydl = MagicMock()
    mock_ydl_cls.return_value.__enter__.return_value = mock_ydl

    on_progress = MagicMock()

    def fake_download(urls):
        hook = _get_hook(mock_ydl_cls)
        hook({"status": "downloading", "downloaded_bytes": 25, "total_bytes_estimate": 100})
        hook({"status": "finished", "filename": "/tmp/some/path.webm"})

    mock_ydl.download.side_effect = fake_download

    download_audio("https://youtube.com/watch?v=abc123", "/tmp/some", on_progress=on_progress)

    on_progress.assert_called_once_with(25.0)


@patch("audioforge.core.downloader.yt_dlp.YoutubeDL")
def test_download_audio_happy_path_returns_finished_path(mock_ydl_cls):
    mock_ydl = MagicMock()
    mock_ydl_cls.return_value.__enter__.return_value = mock_ydl

    def fake_download(urls):
        hook = _get_hook(mock_ydl_cls)
        hook({"status": "finished", "filename": "/tmp/some/path.webm"})

    mock_ydl.download.side_effect = fake_download

    result = download_audio("https://youtube.com/watch?v=abc123", "/tmp/some")

    assert result == "/tmp/some/path.webm"


@patch("audioforge.core.downloader.yt_dlp.YoutubeDL")
def test_download_audio_raises_when_no_finished_hook_fired(mock_ydl_cls):
    mock_ydl = MagicMock()
    mock_ydl_cls.return_value.__enter__.return_value = mock_ydl
    # download() completes without ever invoking the hook with status "finished"
    mock_ydl.download.return_value = None

    with pytest.raises(DownloadError, match="no output file was reported"):
        download_audio("https://youtube.com/watch?v=abc123", "/tmp/some")
