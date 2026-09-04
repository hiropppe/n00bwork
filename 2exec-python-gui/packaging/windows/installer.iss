; Inno Setup スクリプト: A と B_worker を1インストーラにまとめる。
;
; 前提: Makefile の build-b → build-a → assemble を実行済みで、
;   dist/app_a/ に app_a.exe と b_worker.exe（+ それぞれの依存）が同居している。
;
; ポイント:
;   - スタートメニューのショートカットは A（app_a.exe）だけを指す。
;     ユーザが起動するのは A だけ。B は A が QProcess で起動する。
;   - A は Path(sys.executable).parent / "b_worker.exe" で B を解決するので、
;     両者を同一ディレクトリにインストールする。

#define MyAppName "Stats GUI (A + B_worker)"
#define MyAppVersion "0.1.0"
#define MyAppPublisher "n00bwork"
#define MyAppExeName "app_a.exe"

[Setup]
AppId={{B2A7F3C1-2E4D-4A9B-9C3E-2EXEC0000001}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\StatsGUI
DefaultGroupName=Stats GUI
DisableProgramGroupPage=yes
OutputBaseFilename=StatsGUI-Setup-{#MyAppVersion}
Compression=lzma
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Files]
; assemble 済みの dist/app_a/ をまるごと配置する。構成は:
;   {app}\app_a.exe          … A 本体
;   {app}\_internal\         … A の依存（PySide6。numpy は無い）
;   {app}\b_worker\b_worker.exe と {app}\b_worker\_internal\ … B 一式（numpy）
; A は Path(sys.executable).parent \ "b_worker" \ "b_worker.exe" で B を解決する。
Source: "..\..\dist\app_a\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
; ショートカットは A だけ。B_worker は指さない。
Name: "{group}\Stats GUI"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Uninstall Stats GUI"; Filename: "{uninstallexe}"
Name: "{autodesktop}\Stats GUI"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "デスクトップにショートカットを作成"; GroupDescription: "追加アイコン:"; Flags: unchecked

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Stats GUI を起動"; Flags: nowait postinstall skipifsilent
