# Packaging & Distribution Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (this plan is mostly manual/build-tool steps, not TDD).

**Goal:** Produce a single-file Windows installer the studio can run without installing Python.

**Architecture:** PyInstaller bundles `audioforge.app:main` plus PySide6/yt-dlp/mutagen into a `dist/AudioForge/` folder (`--onedir`, not `--onefile`, so startup stays fast); Inno Setup wraps that folder into `AudioForge-Setup-<version>.exe`. FFmpeg is NOT bundled by default (licensing + binary size) — the installer checks for FFmpeg on first run and, if absent, links the user to the official FFmpeg Windows build page and lets them set a custom path in Settings.

**Tech Stack:** PyInstaller, Inno Setup (`ISCC.exe`).

**Spec:** [00-overview.md](00-overview.md) Phase 4, [ORIGINAL_BRIEF.md](ORIGINAL_BRIEF.md) §3, §9

## Global Constraints

- Do not bundle FFmpeg binaries in the git repo or the installer unless the studio explicitly asks and confirms they've reviewed FFmpeg's LGPL/GPL build licensing implications for redistribution.
- Version number lives in exactly one place: `pyproject.toml`'s `[project].version` — the PyInstaller spec and Inno Setup script both read it at build time, never hardcode it twice.
- The build must be reproducible from a clean checkout: `pip install -e .[build]` + one build script, no manual steps beyond running Inno Setup.

---

### Task 1: PyInstaller spec file

**Files:**
- Create: `packaging/audioforge.spec`
- Modify: `requirements-dev.txt` (add `pyinstaller>=6.0`)

- [ ] **Step 1: Add `pyinstaller>=6.0` to `requirements-dev.txt` and install it**

Run: `pip install pyinstaller`

- [ ] **Step 2: Generate an initial spec, then hand-edit it**

Run: `pyi-makespec --name AudioForge --windowed --icon packaging/icon.ico src/audioforge/app.py --specpath packaging`

- [ ] **Step 3: Edit `packaging/audioforge.spec` to include hidden imports PyInstaller misses for yt-dlp's dynamic plugin loading**

```python
# packaging/audioforge.spec (key additions after pyi-makespec generates the base file)
hiddenimports = ["yt_dlp.extractor", "mutagen.easyid3", "mutagen.flac", "mutagen.mp4", "mutagen.oggopus"]
```//merge this into the Analysis(...) call's `hiddenimports=` argument.

- [ ] **Step 4: Build and smoke-test**

Run:
```powershell
pyinstaller packaging/audioforge.spec --distpath dist --workpath build
dist\AudioForge\AudioForge.exe
```
Expected: app launches, shows disclaimer, opens main window — same behavior as `python -m audioforge.app`.

- [ ] **Step 5: Commit** — `git add packaging/audioforge.spec requirements-dev.txt && git commit -m "build: add PyInstaller spec for AudioForge"`

(Do not commit `dist/`, `build/` — already covered by `.gitignore` from sub-plan 1.)

---

### Task 2: Inno Setup installer script

**Files:**
- Create: `packaging/installer.iss`

- [ ] **Step 1: Write the Inno Setup script**

```ini
; packaging/installer.iss
#define MyAppName "AudioForge"
#define MyAppVersion "0.1.0"
#define MyAppExeName "AudioForge.exe"

[Setup]
AppName={#MyAppName}
AppVersion={#MyAppVersion}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
OutputBaseFilename=AudioForge-Setup-{#MyAppVersion}
OutputDir=..\dist\installer
Compression=lzma2
SolidCompression=yes

[Files]
Source: "..\dist\AudioForge\*"; DestDir: "{app}"; Flags: recursesubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; Flags: unchecked
```

Note: `MyAppVersion` must be bumped to match `pyproject.toml` on every release build — track this manually until sub-plan 8's scope is revisited to script it.

- [ ] **Step 2: Build the installer**

Run (from an Inno Setup install with `ISCC.exe` on PATH): `ISCC packaging\installer.iss`
Expected: `dist/installer/AudioForge-Setup-0.1.0.exe` produced.

- [ ] **Step 3: Manual install test**

Run the produced installer on a clean Windows test account/VM without Python installed; verify the app launches and the disclaimer/settings/queue all work without a Python interpreter present.

- [ ] **Step 4: Commit** — `git add packaging/installer.iss && git commit -m "build: add Inno Setup installer script"`
