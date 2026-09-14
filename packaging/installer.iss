; packaging/installer.iss
;
; MyAppVersion is NOT hardcoded here. It must be supplied at compile time via
; the /D command-line switch, e.g.:
;   ISCC /DMyAppVersion=0.1.0 packaging\installer.iss
; packaging/build.ps1 does this automatically, reading the version from
; pyproject.toml (the single source of truth per this plan's Global
; Constraints) so it is never duplicated by hand.
#ifndef MyAppVersion
  #define MyAppVersion "0.0.0-dev"
#endif

#define MyAppName "AudioForge"
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
