import os

from audioforge import config


def test_get_db_path_resolves_under_appdata_and_creates_parent(tmp_path, monkeypatch):
    fake_appdata = tmp_path / "AppData" / "Roaming"
    monkeypatch.setattr(os, "getenv", lambda name, default=None: str(fake_appdata) if name == "APPDATA" else default)

    db_path = config.get_db_path()

    assert db_path.endswith("audioforge.db")
    assert os.path.isdir(os.path.dirname(db_path))
    assert os.path.dirname(db_path) == str(fake_appdata / "AudioForge")


def test_get_db_path_falls_back_when_appdata_unset(tmp_path, monkeypatch):
    fake_home = tmp_path / "home"
    monkeypatch.setattr(os, "getenv", lambda name, default=None: None if name == "APPDATA" else default)
    monkeypatch.setattr(os.path, "expanduser", lambda p: p.replace("~", str(fake_home)))

    db_path = config.get_db_path()

    assert db_path.endswith("audioforge.db")
    assert os.path.isdir(os.path.dirname(db_path))
