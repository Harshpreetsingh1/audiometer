; ============================================================
; Audiometry Pro - Inno Setup Script
; ============================================================
; USAGE:
;   Interactive:  Audiometry_Setup.exe
;   Silent:       Audiometry_Setup.exe /SILENT
;   Very Silent:  Audiometry_Setup.exe /VERYSILENT
;
; Prerequisites:
;   1. Run build.bat first to create dist\Audiometry_Pro.exe
;   2. Open this file in Inno Setup Compiler and click Compile
; ============================================================

#define MyAppName "Audiometry Pro"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Audiometry Solutions"
#define MyAppExeName "Audiometry_Pro.exe"

[Setup]
AppId={{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
OutputDir=Output
OutputBaseFilename=Audiometry_Setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
DisableProgramGroupPage=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; Flags: checkedonce

[Files]
Source: "dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch Audiometry Pro"; Flags: nowait postinstall skipifsilent
