#define MyAppName "EvaluaFPCanarias"
#define MyAppVersion "1.0.2"
#define MyAppPublisher "Francisco Javier Gonzalez Rolo"
#define MyAppExeName "EvaluaFPCanarias.exe"
[Setup]
AppId={{ED3CDA7D-521C-4D31-BBC7-4A00E3AC91F0}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={localappdata}\Programs\EvaluaFPCanarias
DefaultGroupName=EvaluaFPCanarias
OutputDir=..\dist
OutputBaseFilename=Instalar_EvaluaFPCanarias
Compression=lzma2
SolidCompression=yes
PrivilegesRequired=lowest
WizardStyle=modern
SetupIconFile=..\assets\EvaluaFP.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
CloseApplications=yes
DisableProgramGroupPage=yes
[Files]
Source: "..\dist\EvaluaFPCanarias.exe"; DestDir: "{app}"; Flags: ignoreversion
[Icons]
Name: "{group}\EvaluaFPCanarias"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\EvaluaFPCanarias"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon
[Tasks]
Name: "desktopicon"; Description: "Crear acceso directo en el escritorio"; GroupDescription: "Accesos directos:"
[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Iniciar EvaluaFPCanarias"; Flags: nowait postinstall skipifsilent
