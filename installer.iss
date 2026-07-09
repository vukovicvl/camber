; Camber — Inno Setup installer script
; Creates a proper Windows installer with Start Menu, Desktop shortcut, and uninstaller
;
; Prerequisites:
;   1. Build with PyInstaller first: pyinstaller camber.spec
;   2. Install Inno Setup from https://jrsoftware.org/isinfo.php
;   3. Open this file in Inno Setup Compiler and click Build
;
; Output: installer/Camber_Setup.exe

[Setup]
AppName=Camber
AppVersion=0.1.0
AppPublisher=Camber Project
AppPublisherURL=https://github.com/vukovicvl/camber
DefaultDirName={autopf}\Camber
DefaultGroupName=Camber
OutputDir=installer
OutputBaseFilename=Camber_Setup
SetupIconFile=camber_icon.ico
UninstallDisplayIcon={app}\Camber.exe
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=

ArchitecturesInstallIn64BitMode=x64compatible
DisableProgramGroupPage=yes
PrivilegesRequired=lowest

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Files]
Source: "dist\Camber\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs

[Icons]
Name: "{group}\Camber"; Filename: "{app}\Camber.exe"
Name: "{autodesktop}\Camber"; Filename: "{app}\Camber.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create desktop shortcut"; GroupDescription: "Additional shortcuts:"

[Run]
Filename: "{app}\Camber.exe"; Description: "Launch Camber"; Flags: nowait postinstall skipifsilent
