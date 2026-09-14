# packaging/build.ps1
#
# Reproducible build: PyInstaller onedir bundle + (if Inno Setup is
# installed) the Windows installer. Reads the version from pyproject.toml
# once, so it is never hardcoded anywhere else.
#
# Usage (from repo root, with a venv that has `pip install -e .[build]` done):
#   powershell -ExecutionPolicy Bypass -File packaging\build.ps1

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

# 1. Read the single-sourced version from pyproject.toml.
$pyprojectContent = Get-Content -Raw "pyproject.toml"
if ($pyprojectContent -notmatch 'version\s*=\s*"([^"]+)"') {
    throw "Could not find [project].version in pyproject.toml"
}
$Version = $Matches[1]
Write-Host "AudioForge version: $Version"

# 2. Build the PyInstaller onedir bundle.
pyinstaller packaging\audioforge.spec --distpath dist --workpath build --noconfirm
if ($LASTEXITCODE -ne 0) { throw "PyInstaller build failed" }

# 3. Build the Inno Setup installer, if ISCC.exe is available on PATH.
$iscc = Get-Command ISCC.exe -ErrorAction SilentlyContinue
if ($iscc) {
    & $iscc.Source "/DMyAppVersion=$Version" "packaging\installer.iss"
    if ($LASTEXITCODE -ne 0) { throw "Inno Setup build failed" }
    Write-Host "Installer written to dist\installer\AudioForge-Setup-$Version.exe"
} else {
    Write-Warning "ISCC.exe (Inno Setup) not found on PATH - skipping installer build."
    Write-Warning "Install Inno Setup (https://jrsoftware.org/isinfo.php) and re-run this script,"
    Write-Warning "or run manually: ISCC /DMyAppVersion=$Version packaging\installer.iss"
}
