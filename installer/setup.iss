#define MyAppName "RAR PDF Batch Unlocker"
#define MyAppVersion "1.0.0"
#define MyAppExeName "RAR-PDF-Batch-Unlocker.exe"
[Setup]
AppId={{F7D334A0-9E8C-4D21-BA8F-E82B624AB155}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher=RAR Tools
DefaultDirName={autopf}\RAR PDF Batch Unlocker
DefaultGroupName={#MyAppName}
OutputDir=..\release
OutputBaseFilename=RAR-PDF-Batch-Unlocker-Setup
Compression=lzma2
SolidCompression=yes
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64
WizardStyle=modern
PrivilegesRequired=lowest
UninstallDisplayIcon={app}\{#MyAppExeName}
DisableProgramGroupPage=yes
[Files]
Source: "..\dist\RAR-PDF-Batch-Unlocker\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon
[Tasks]
Name: "desktopicon"; Description: "Create desktop shortcut"; GroupDescription: "Additional icons:"
[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent
