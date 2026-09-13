# Environment & Repo Setup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Stand up the Python project skeleton, dependency management, and test runner so every later sub-plan can add code and tests immediately.

**Architecture:** Standard `src/` layout Python package `audioforge`, installed editable via pip, tested with pytest. No packaging/build step yet (that's sub-plan 8).

**Tech Stack:** Python 3.11+, pip + `requirements.txt`, pytest, PySide6, yt-dlp, mutagen.

**Spec:** [00-overview.md](00-overview.md), [ORIGINAL_BRIEF.md](ORIGINAL_BRIEF.md)

## Global Constraints

- Windows 10/11 primary target.
- No network calls in unit tests.
- All modules importable as `audioforge.core.*`, `audioforge.ui.*`, `audioforge.workers.*`.

---

### Task 1: Repo skeleton and dependency files

**Files:**
- Create: `requirements.txt`
- Create: `requirements-dev.txt`
- Create: `pyproject.toml`
- Create: `.gitignore`
- Create: `src/audioforge/__init__.py`
- Create: `src/audioforge/core/__init__.py`
- Create: `src/audioforge/workers/__init__.py`
- Create: `src/audioforge/ui/__init__.py`
- Create: `tests/__init__.py`
- Create: `tests/core/__init__.py`
- Create: `README.md`

**Interfaces:**
- Produces: an installable package `audioforge` importable from `tests/` once installed with `pip install -e .`.

- [ ] **Step 1: Write `pyproject.toml`**

```toml
[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "audioforge"
version = "0.1.0"
description = "Desktop audio downloader & converter for music production studios"
requires-python = ">=3.11"
authors = [{ name = "Lapalu Liyanage" }]

[tool.setuptools.packages.find]
where = ["src"]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

- [ ] **Step 2: Write `requirements.txt`**

```
PySide6>=6.7
yt-dlp>=2024.8.6
mutagen>=1.47
```

- [ ] **Step 3: Write `requirements-dev.txt`**

```
-r requirements.txt
pytest>=8.0
pytest-qt>=4.4
```

- [ ] **Step 4: Write `.gitignore`**

```
__pycache__/
*.pyc
.venv/
venv/
build/
dist/
*.egg-info/
.pytest_cache/
audioforge.db
downloads/
*.spec
```

- [ ] **Step 5: Create empty `__init__.py` files listed above**

Each file's content is just:

```python
```

(empty package marker)

- [ ] **Step 6: Write `README.md`**

```markdown
# AudioForge

Desktop audio downloader & converter for music production studios.

## Development setup

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements-dev.txt
pip install -e .
```

## Running tests

```powershell
pytest
```

## Running the app

```powershell
python -m audioforge.app
```

See `docs/plan/00-overview.md` for the full development plan.
```

- [ ] **Step 7: Create venv, install deps, verify import**

Run:
```powershell
python -m venv .venv
.venv\Scripts\pip install -r requirements-dev.txt
.venv\Scripts\pip install -e .
.venv\Scripts\python -c "import audioforge; print('ok')"
```
Expected: prints `ok` with no errors.

- [ ] **Step 8: Verify pytest runs with zero tests collected (no errors)**

Run: `.venv\Scripts\pytest -q`
Expected: `no tests ran` (exit code 5) or similar, no import errors.

- [ ] **Step 9: Commit**

```bash
git add pyproject.toml requirements.txt requirements-dev.txt .gitignore README.md src tests
git commit -m "chore: scaffold audioforge project skeleton"
```

---

### Task 2: FFmpeg/yt-dlp availability check utility

**Files:**
- Create: `src/audioforge/core/deps.py`
- Test: `tests/core/test_deps.py`

**Interfaces:**
- Produces: `find_ffmpeg() -> str | None`, `check_dependencies() -> dict[str, bool]` — later sub-plans (converter, downloader) call `find_ffmpeg()` to locate the FFmpeg binary before shelling out.

- [ ] **Step 1: Write the failing test**

```python
# tests/core/test_deps.py
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
    assert result["yt_dlp"] is True  # installed via requirements.txt
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/core/test_deps.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'audioforge.core.deps'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/audioforge/core/deps.py
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/core/test_deps.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add src/audioforge/core/deps.py tests/core/test_deps.py
git commit -m "feat: add ffmpeg/yt-dlp dependency detection"
```
