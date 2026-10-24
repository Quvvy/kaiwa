; Inno Setup 6 - wraps the dist\Kaiwa\ tree into a Windows installer.
; Build: .\scripts\build_installer.ps1  (requires Inno Setup 6 / ISCC.exe)
; The script passes /DMyAppVersion=<kaiwa.__version__> and makes the wizard
; images under build\installer\.
;
; Uninstall removes the program. Progress, models and the voice engine under
; %LocalAppData%\Kaiwa\ stay unless the learner chooses to remove them.

#ifndef MyAppVersion
  #error Pass /DMyAppVersion=x.y.z (scripts\build_installer.ps1 does this).
#endif
#define MyAppName "Kaiwa"
#define MyAppPublisher "Kaiwa"
#define MyAppExeName "Kaiwa.exe"
#define MyAppURL "https://github.com/Quvvy/kaiwa"
; Must match MUTEX_NAME in src\kaiwa\desktop\instance.py.
#define MyAppMutex "KaiwaDesktopSingleInstance"

[Setup]
; Fixed AppId - do not change between releases (Add/Remove Programs identity).
AppId={{E8F2A1B0-4C5D-4E6F-9A8B-1C2D3E4F5A6B}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}/issues
AppUpdatesURL={#MyAppURL}/releases
AppCopyright=Copyright (c) 2026 Kaiwa contributors
AppMutex={#MyAppMutex},Global\{#MyAppMutex}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
DisableWelcomePage=no
LicenseFile=..\LICENSE
OutputDir=..\dist
OutputBaseFilename=KaiwaSetup-{#MyAppVersion}
SetupIconFile=..\src\kaiwa\desktop\assets\kaiwa.ico
WizardStyle=modern
WizardSizePercent=100
WizardImageFile=..\build\installer\wizard-large.bmp,..\build\installer\wizard-large-2x.bmp
WizardSmallImageFile=..\build\installer\wizard-small.bmp,..\build\installer\wizard-small-2x.bmp
; Size: one solid LZMA2 stream at the highest setting; most of the payload is
; native libraries (Whisper, ONNX, FFmpeg) that compress well together.
Compression=lzma2/ultra64
SolidCompression=yes
LZMAUseSeparateProcess=yes
LZMANumBlockThreads=4
MinVersion=10.0
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=admin
; Updating while Kaiwa runs: offer to close it (and its background processes).
CloseApplications=yes
CloseApplicationsFilter=*.exe,*.dll,*.pyd
RestartApplications=no
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayName={#MyAppName}
VersionInfoVersion={#MyAppVersion}.0
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription={#MyAppName} Setup
VersionInfoProductName={#MyAppName}
VersionInfoProductVersion={#MyAppVersion}
SetupLogging=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[InstallDelete]
; Updating from 1.x: the old runtime was a venv with a different layout, and
; stale packages or pages must not survive next to the new ones.
Type: filesandordirs; Name: "{app}\runtime"
Type: filesandordirs; Name: "{app}\_internal"
Type: filesandordirs; Name: "{app}\static"

[Files]
Source: "..\dist\Kaiwa\*"; DestDir: "{app}"; Excludes: "Kaiwa.portable,Data\*"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\LICENSE"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\NOTICE.md"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
; Taskbar pins and these shortcuts all point at Kaiwa.exe, which keeps
; Windows' default identity, so a pinned Kaiwa and the open window share one button.
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
; runasoriginaluser: Setup runs elevated, but Kaiwa must start as the learner,
; or its settings and progress would land in the wrong place.
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent runasoriginaluser

[UninstallDelete]
; Bytecode Python may have written next to the runtime.
Type: filesandordirs; Name: "{app}\runtime"
Type: filesandordirs; Name: "{app}\static"

[Code]
function KaiwaDataDir(): String;
begin
  Result := ExpandConstant('{localappdata}\Kaiwa');
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if (CurUninstallStep = usPostUninstall) and (not UninstallSilent) and DirExists(KaiwaDataDir()) then
  begin
    if MsgBox('Also delete your Kaiwa progress and downloads?' + #13#10 + #13#10 +
              'This removes your lessons, reviews, settings, API key, the speech model and the voice engine in:' + #13#10 +
              KaiwaDataDir() + #13#10 + #13#10 +
              'Choose No to keep them for a later reinstall.',
              mbConfirmation, MB_YESNO or MB_DEFBUTTON2) = IDYES then
      DelTree(KaiwaDataDir(), True, True, True);
  end;
end;
