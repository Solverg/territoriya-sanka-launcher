#ifndef AppVersion
  #define AppVersion "1.1.0"
#endif

#define AppName "Территория Санька: Королевская Битва"
#define AppExeName "TerritorySanyokLauncher.exe"

[Setup]
AppId={{765751C7-5E74-44C4-9A9A-EE6BCA3ED1B4}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=Solverg
DefaultDirName={localappdata}\Programs\TerritorySanyokLauncher
DefaultGroupName={#AppName}
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
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\run-launcher.cmd"; WorkingDir: "{app}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\run-launcher.cmd"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\run-launcher.cmd"; Description: "Открыть лаунчер"; Flags: nowait postinstall skipifsilent

