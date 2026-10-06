#ifndef AppVersion
  #define AppVersion "1.3.2"
#endif

#define AppId "{{765751C7-5E74-44C4-9A9A-EE6BCA3ED1B4}"
#define AppName "Территория Санька: Королевская Битва"
#define AppShortcutName "Территория Санька - Королевская Битва"
#define AppDesktopShortcutName "Территория Санька"
#define AppExeName "TerritorySanyokLauncher.exe"

[Setup]
AppId={#AppId}
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
; Let Windows Restart Manager ask the player to close a running launcher
; before replacing its files. It never targets the game process.
CloseApplications=yes
RestartApplications=no

[Tasks]
Name: "desktopicon"; Description: "Создать ярлык на рабочем столе"; Flags: unchecked

[Files]
Source: "..\release\{#AppVersion}\launcher\*"; DestDir: "{app}"; Excludes: "launcher.config.json"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\release\{#AppVersion}\launcher\launcher.config.json"; DestDir: "{app}"; Flags: onlyifdoesntexist

[Icons]
Name: "{autoprograms}\{#AppShortcutName}"; Filename: "{app}\{#AppExeName}"; WorkingDir: "{app}"
Name: "{autodesktop}\{#AppDesktopShortcutName}"; Filename: "{app}\{#AppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExeName}"; Description: "Открыть лаунчер"; Flags: nowait postinstall skipifsilent

[Code]
function GetInstallDir(Param: String): String;
var
  LocalAppData: String;
  PreviousDir: String;
begin
  if RegQueryStringValue(HKCU, 'Software\Microsoft\Windows\CurrentVersion\Uninstall\{#AppId}_is1', 'Inno Setup: App Path', PreviousDir) and DirExists(PreviousDir) then
    Result := PreviousDir
  else begin
    LocalAppData := GetEnv('LOCALAPPDATA');
    if LocalAppData <> '' then
      Result := AddBackslash(LocalAppData) + 'Programs\TerritorySanyokLauncher'
    else
      Result := ExpandConstant('{userdocs}\Apps\TerritorySanyokLauncher');
  end;
end;

function VersionPart(const Version: String; PartIndex: Integer): Integer;
var
  Position: Integer;
  StartPosition: Integer;
  CurrentPart: Integer;
begin
  StartPosition := 1;
  CurrentPart := 0;
  for Position := 1 to Length(Version) + 1 do begin
    if (Position > Length(Version)) or (Version[Position] = '.') then begin
      if CurrentPart = PartIndex then begin
        Result := StrToIntDef(Copy(Version, StartPosition, Position - StartPosition), 0);
        exit;
      end;
      CurrentPart := CurrentPart + 1;
      StartPosition := Position + 1;
    end;
  end;
  Result := 0;
end;

function CompareLauncherVersions(const InstalledVersion: String; const AvailableVersion: String): Integer;
var
  PartIndex: Integer;
  InstalledPart: Integer;
  AvailablePart: Integer;
begin
  Result := 0;
  for PartIndex := 0 to 3 do begin
    InstalledPart := VersionPart(InstalledVersion, PartIndex);
    AvailablePart := VersionPart(AvailableVersion, PartIndex);
    if InstalledPart < AvailablePart then begin
      Result := -1;
      exit;
    end;
    if InstalledPart > AvailablePart then begin
      Result := 1;
      exit;
    end;
  end;
end;

function InitializeSetup(): Boolean;
var
  InstalledVersion: String;
  VersionOrder: Integer;
begin
  Result := True;
  if not RegQueryStringValue(HKCU, 'Software\Microsoft\Windows\CurrentVersion\Uninstall\{#AppId}_is1', 'DisplayVersion', InstalledVersion) then
    exit;

  VersionOrder := CompareLauncherVersions(InstalledVersion, '{#AppVersion}');
  if VersionOrder > 0 then begin
    MsgBox(
      'Уже установлена более новая версия ' + InstalledVersion +
      '. Установка версии {#AppVersion} отменена, чтобы не понизить лаунчер.',
      mbError, MB_OK);
    Result := False;
  end else if VersionOrder < 0 then
    MsgBox(
      'Найдена версия ' + InstalledVersion + '. Она будет обновлена до версии {#AppVersion} в той же папке.',
      mbInformation, MB_OK)
  else
    MsgBox(
      'Версия {#AppVersion} уже установлена. Установщик проверит и восстановит файлы лаунчера в той же папке.',
      mbInformation, MB_OK);
end;
