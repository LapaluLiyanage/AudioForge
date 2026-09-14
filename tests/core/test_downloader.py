from unittest.mock import MagicMock, patch

import pytest

from audioforge.core.downloader import probe
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
