#ifndef AppVersion
  #define AppVersion "1.1.0"
#endif

#define AppName "Территория Санька: Королевская Битва"
#define AppShortcutName "Территория Санька - Королевская Битва"
#define AppExeName "TerritorySanyokLauncher.exe"

[Setup]
AppId={{765751C7-5E74-44C4-9A9A-EE6BCA3ED1B4}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=Solverg
; The destination is provided by GetInstallDir below. It reads LOCALAPPDATA
; directly so restricted Windows profiles do not need Inno's shell-folder lookup.
DefaultDirName={code:GetInstallDir}
; A colon is valid in the display name but forbidden in Windows file paths.
; Keep all directory and .lnk names separate from the branded display name.
DefaultGroupName={#AppShortcutName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=..\release\{#AppVersion}
OutputBaseFilename=TerritorySanyokLauncher-Setup-{#AppVersion}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
UninstallDisplayName={#AppName}

[Tasks]
Name: "desktopicon"; Description: "Создать ярлык на рабочем столе"; Flags: unchecked

[Files]
Source: "..\release\{#AppVersion}\launcher\*"; DestDir: "{app}"; Excludes: "launcher.config.json"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\release\{#AppVersion}\launcher\launcher.config.json"; DestDir: "{app}"; Flags: onlyifdoesntexist

[Icons]
Name: "{autoprograms}\{#AppShortcutName}"; Filename: "{app}\run-launcher.cmd"; WorkingDir: "{app}"
Name: "{autodesktop}\{#AppShortcutName}"; Filename: "{app}\run-launcher.cmd"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\run-launcher.cmd"; Description: "Открыть лаунчер"; Flags: nowait postinstall skipifsilent

[Code]
function GetInstallDir(Param: String): String;
var
  LocalAppData: String;
begin
  LocalAppData := GetEnv('LOCALAPPDATA');
  if LocalAppData <> '' then
    Result := AddBackslash(LocalAppData) + 'Programs\TerritorySanyokLauncher'
  else
    Result := ExpandConstant('{userdocs}\Apps\TerritorySanyokLauncher');
end;

