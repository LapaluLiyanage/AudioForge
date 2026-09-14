from audioforge.core.models import TrackMetadata
from audioforge.core.organizer import resolve_output_path, sanitize_filename


def make_meta(title="My Song: Remix?"):
    return TrackMetadata(id="1", title=title, uploader="Ch", duration_seconds=1, url="u")


def test_sanitize_filename_strips_illegal_characters():
    assert sanitize_filename('My Song: Remix?/\\<>') == "My Song Remix"


def test_resolve_output_path_builds_project_subfolder(tmp_path):
    path = resolve_output_path(str(tmp_path), "ClientA", make_meta("Track One"), "wav")
    assert path == str(tmp_path / "ClientA" / "Track One.wav")


def test_resolve_output_path_dedupes_existing_file(tmp_path):
    (tmp_path / "ClientA").mkdir()
    (tmp_path / "ClientA" / "Track One.wav").write_bytes(b"x")

    path = resolve_output_path(str(tmp_path), "ClientA", make_meta("Track One"), "wav")

    assert path == str(tmp_path / "ClientA" / "Track One (2).wav")


def test_resolve_output_path_creates_project_folder(tmp_path):
    project_dir = tmp_path / "ClientA"
    assert not project_dir.exists()

    resolve_output_path(str(tmp_path), "ClientA", make_meta("Track One"), "wav")

    assert project_dir.is_dir()
