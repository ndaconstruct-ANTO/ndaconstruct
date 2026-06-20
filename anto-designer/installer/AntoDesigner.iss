; ============================================================
;  ANTO DESIGNER - Script d'installateur Windows (Inno Setup)
;  Pre-requis : Inno Setup 6  (https://jrsoftware.org/isinfo.php)
;  Avant : construire l'app avec  tools\build_windows.bat
;          (produit dist\AntoDesigner\)
;  Ensuite : ouvrir ce fichier dans Inno Setup et cliquer "Compile".
;  Resultat : installer\Output\AntoDesigner-Setup.exe
; ============================================================

#define AppName "ANTO DESIGNER"
#define AppVersion "0.1.0"
#define AppExe "AntoDesigner.exe"
#define Publisher "Anto"

[Setup]
AppId={{B9F1B0E2-1A2B-4C3D-9E4F-ANTODESIGNER01}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#Publisher}
DefaultDirName={autopf}\AntoDesigner
DefaultGroupName=ANTO DESIGNER
DisableProgramGroupPage=yes
OutputBaseFilename=AntoDesigner-Setup
OutputDir=Output
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
SetupIconFile=..\anto_designer\assets\icon.ico
UninstallDisplayIcon={app}\{#AppExe}
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "french"; MessagesFile: "compiler:Languages\French.isl"

[Tasks]
Name: "desktopicon"; Description: "Créer un raccourci sur le Bureau"; GroupDescription: "Raccourcis :"

[Files]
; Tout le dossier produit par PyInstaller (onedir).
Source: "..\dist\AntoDesigner\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{group}\ANTO DESIGNER"; Filename: "{app}\{#AppExe}"
Name: "{group}\Désinstaller ANTO DESIGNER"; Filename: "{uninstallexe}"
Name: "{autodesktop}\ANTO DESIGNER"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExe}"; Description: "Lancer ANTO DESIGNER"; Flags: nowait postinstall skipifsilent

; NOTE : les projets de l'utilisateur sont stockes dans %APPDATA%\AntoDesigner
; et ne sont PAS supprimes a la desinstallation (conserves par defaut).
