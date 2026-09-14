"""Application paths, defaults, and settings persistence helpers."""
from __future__ import annotations

import os

APP_DIR_NAME = "AudioForge"
DB_FILE_NAME = "audioforge.db"


def get_db_path() -> str:
    """Return the path to the AudioForge job queue database.

    Resolves to ``%APPDATA%/AudioForge/audioforge.db`` on Windows. If
    ``APPDATA`` is unset (e.g. non-Windows or test environments), falls back
    to a path under the user's home directory. Ensures the parent directory
    exists before returning.
    """
    appdata = os.getenv("APPDATA")
    if appdata:
        app_dir = os.path.join(appdata, APP_DIR_NAME)
    else:
        app_dir = os.path.expanduser(os.path.join("~", "." + APP_DIR_NAME.lower()))

    os.makedirs(app_dir, exist_ok=True)
    return os.path.join(app_dir, DB_FILE_NAME)
