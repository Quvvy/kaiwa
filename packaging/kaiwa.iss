; Inno Setup 6 — wraps the portable dist\Kaiwa\ tree into a Windows installer.
; Build: .\scripts\build_installer.ps1  (requires Inno Setup 6 / ISCC.exe)
;
; Uninstall removes Program Files + shortcuts only. User data under
; %LocalAppData%\Kaiwa\ (secrets, models, profiles) is left intact.

#define MyAppName "Kaiwa"
#define MyAppVersion "1.0.3"
#define MyAppPublisher "Kaiwa"
#define MyAppExeName "Kaiwa.exe"
#define MyAppURL "https://github.com/Quvvy/kaiwa"

[Setup]
; Fixed AppId — do not change between releases (Add/Remove Programs identity).
AppId={{E8F2A1B0-4C5D-4E6F-9A8B-1C2D3E4F5A6B}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
LicenseFile=..\LICENSE
InfoAfterFile=
OutputDir=..\dist
OutputBaseFilename=KaiwaSetup-{#MyAppVersion}
SetupIconFile=..\src\kaiwa\desktop\assets\kaiwa.ico
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=admin
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayName={#MyAppName}
VersionInfoVersion={#MyAppVersion}.0
VersionInfoCompany={#MyAppPublisher}
VersionInfoProductName={#MyAppName}
VersionInfoProductVersion={#MyAppVersion}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; Portable release tree from scripts\build_desktop.ps1
Source: "..\dist\Kaiwa\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; Redistribution notices next to the app (NOTICE may already be under dist; overwrite ok)
Source: "..\LICENSE"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\NOTICE.md"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

; Intentionally no [UninstallDelete] for %LocalAppData%\Kaiwa — keep secrets/models.
