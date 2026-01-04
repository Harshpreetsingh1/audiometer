; ============================================================
; Audiometry Pro - Inno Setup Script (One-Click Remote Install)
; ============================================================
; Creates a single-file installer for easy remote deployment.
; 
; USAGE:
;   Interactive:  Audiometry_Setup.exe
;   Silent:       Audiometry_Setup.exe /SILENT
;   Very Silent:  Audiometry_Setup.exe /VERYSILENT
;   
; Silent install auto-creates desktop shortcut and launches app.
;
; Prerequisites:
;   1. Build the .exe first using build.bat
;   2. Install Inno Setup from https://jrsoftware.org/isinfo.php
;   3. Open this file in Inno Setup Compiler and click "Compile"
; ============================================================

#define MyAppName "Audiometry Pro"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Audiometry Solutions"
#define MyAppURL "https://github.com/yourusername/audiometer"
#define MyAppExeName "Audiometry_Pro.exe"

[Setup]
; Unique application identifier
AppId={{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}

; Installation directories
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}

; Output settings
OutputDir=Output
OutputBaseFilename=Audiometry_Setup
; Uncomment if you have an icon file:
; SetupIconFile=audiometer\icon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}

; Compression (maximum for smaller download)
Compression=lzma2/ultra64
SolidCompression=yes

; Modern wizard style
WizardStyle=modern
WizardSizePercent=100

; Allow per-user install (no admin required)
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog

; Cleaner UX
DisableProgramGroupPage=yes
DisableWelcomePage=no
DisableDirPage=auto
DisableReadyPage=yes

; Close running instances before install
CloseApplications=yes
RestartApplications=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
; Desktop icon is checked by default for one-click experience
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: checked

[Files]
; Main executable
Source: "dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
; Start Menu shortcut
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"

; Desktop shortcut
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
; Launch app after installation
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent shellexec

; For silent installs, always launch the app
Filename: "{app}\{#MyAppExeName}"; Flags: nowait shellexec; Check: IsSilentInstall

[Code]
function IsSilentInstall: Boolean;
begin
  Result := WizardSilent();
end;

