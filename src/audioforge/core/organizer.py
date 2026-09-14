"""Output filename sanitization and folder organization."""
from __future__ import annotations

import os
import re

from audioforge.core.models import TrackMetadata

_ILLEGAL_CHARS = re.compile(r'[<>:"/\\|?*]')


def sanitize_filename(name: str) -> str:
    cleaned = _ILLEGAL_CHARS.sub("", name)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned[:200] or "untitled"


def resolve_output_path(base_dir: str, project_name: str, metadata: TrackMetadata, format: str) -> str:
    folder = os.path.join(base_dir, sanitize_filename(project_name))
    stem = sanitize_filename(metadata.title)
    candidate = os.path.join(folder, f"{stem}.{format}")

    counter = 2
    while os.path.exists(candidate):
        candidate = os.path.join(folder, f"{stem} ({counter}).{format}")
        counter += 1
    return candidate
