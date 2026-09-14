import os

import pytest


@pytest.fixture(autouse=True)
def isolated_appdata(tmp_path, monkeypatch):
    """Redirect APPDATA so any code that resolves audioforge's db path
    (e.g. constructing a real MainWindow) never touches the real user's
    AppData folder during tests.
    """
    fake_appdata = tmp_path / "AppData" / "Roaming"
    monkeypatch.setenv("APPDATA", str(fake_appdata))
