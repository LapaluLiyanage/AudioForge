# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for AudioForge. Build with:
    pyinstaller packaging/audioforge.spec --distpath dist --workpath build
"""

a = Analysis(
    ['../src/audioforge/app.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[
        "yt_dlp.extractor",
        "mutagen.easyid3",
        "mutagen.flac",
        "mutagen.mp4",
        "mutagen.oggopus",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='AudioForge',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['icon.ico'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='AudioForge',
)
