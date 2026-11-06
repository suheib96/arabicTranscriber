#define AppName "Arabic Transcriber"
[Setup]
AppId={{7542E58C-C14D-405B-95AA-BD414403BA44}
AppName={#AppName}
AppVersion=0.2.0
DefaultDirName={localappdata}\Programs\ArabicTranscriber
DefaultGroupName={#AppName}
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=..\dist\release
OutputBaseFilename=ArabicTranscriber-Windows-x64-Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\Arabic Transcriber.exe
[Files]
Source: "..\dist\Arabic Transcriber\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\build\MicrosoftEdgeWebview2Setup.exe"; DestDir: "{tmp}"; Flags: deleteafterinstall
[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\Arabic Transcriber.exe"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\Arabic Transcriber.exe"; Tasks: desktopicon
[Tasks]
Name: desktopicon; Description: "Desktop-Verknüpfung erstellen"; Flags: unchecked
[Run]
Filename: "{tmp}\MicrosoftEdgeWebview2Setup.exe"; Parameters: "/silent /install"; StatusMsg: "Microsoft WebView2 wird geprüft und bei Bedarf installiert (Internet erforderlich) …"; Flags: waituntilterminated
Filename: "{app}\Arabic Transcriber.exe"; Description: "Arabic Transcriber starten"; Flags: nowait postinstall skipifsilent
