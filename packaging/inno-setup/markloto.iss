; Instalador Windows Markloto (Inno Setup 6)
; Compilar: ISCC.exe packaging\inno-setup\markloto.iss /DAppVersion=1.0.0
; O ejecutar: scripts\build_windows.ps1

#ifndef AppVersion
#define AppVersion "1.0.0"
#endif

#define AppName "Markloto"
#define AppPublisher "Marcos Calabrés Ibáñez"
#define AppURL "mailto:markbiophysicist@gmail.com"
#define StagingDir "..\..\build\windows-staging"

[Setup]
AppId={{8F4E2A1B-3C5D-4E9F-A1B2-7D8E9F0A1B2C}}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}
AppUpdatesURL={#AppURL}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
AllowNoIcons=yes
LicenseFile=
InfoBeforeFile=
OutputDir=..\..\dist\installers\windows-x64
OutputBaseFilename=Markloto-{#AppVersion}-win64-Setup
SetupIconFile=
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=admin
PrivilegesRequiredOverridesAllowed=dialog
DisableProgramGroupPage=no
UninstallDisplayIcon={app}\Markloto.exe
VersionInfoVersion={#AppVersion}.0
VersionInfoCompany={#AppPublisher}
VersionInfoDescription=Asistencia informativa para Primitiva, Bonoloto y Euromillones
VersionInfoProductName={#AppName}
VersionInfoProductVersion={#AppVersion}

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "desktopicon"; Description: "Crear un icono en el escritorio"; GroupDescription: "Tareas adicionales:"; Flags: unchecked

[Files]
Source: "{#StagingDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "LEEME-instalacion.txt"; DestDir: "{app}"; Flags: isreadme

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\Markloto.exe"; Comment: "Markloto - analisis de loterias"
Name: "{group}\Desinstalar {#AppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\Markloto.exe"; Tasks: desktopicon; Comment: "Markloto"

[Run]
Filename: "{app}\Markloto.exe"; Description: "Iniciar {#AppName}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; No borrar %LOCALAPPDATA%\Markloto (base de datos del usuario)
