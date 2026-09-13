from audioforge.core import deps


def test_find_ffmpeg_returns_none_when_not_on_path(monkeypatch):
    monkeypatch.setattr(deps.shutil, "which", lambda name: None)
    assert deps.find_ffmpeg() is None


def test_find_ffmpeg_returns_path_when_on_path(monkeypatch):
    monkeypatch.setattr(deps.shutil, "which", lambda name: r"C:\ffmpeg\ffmpeg.exe")
    assert deps.find_ffmpeg() == r"C:\ffmpeg\ffmpeg.exe"


def test_check_dependencies_reports_ffmpeg_and_ytdlp():
    result = deps.check_dependencies()
    assert "ffmpeg" in result
    assert "yt_dlp" in result
    assert result["yt_dlp"] is True
