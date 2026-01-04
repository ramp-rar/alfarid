; Inno Setup скрипт для Alfarid Installer
; Требуется: Inno Setup 6+ (https://jrsoftware.org/isdl.php)

#define MyAppName "Alfarid"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Alfarid Team"
#define MyAppURL "https://alfarid.example.com"

[Setup]
AppId={{8F9A6B2C-1D3E-4F5A-9B7C-2E8D6F4A3B1C}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
OutputDir=..\installer
OutputBaseFilename=Alfarid-Setup-{#MyAppVersion}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
ArchitecturesInstallIn64BitMode=x64

[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Types]
Name: "full"; Description: "Полная установка"
Name: "teacher"; Description: "Только приложение преподавателя"
Name: "student"; Description: "Только приложение студента"
Name: "custom"; Description: "Выборочная установка"; Flags: iscustom

[Components]
Name: "teacher"; Description: "Alfarid Teacher (Преподаватель)"; Types: full teacher custom; Flags: fixed
Name: "student"; Description: "Alfarid Student (Студент)"; Types: full student custom
Name: "backend"; Description: "Backend API Server (Опционально)"; Types: full custom

[Tasks]
Name: "desktopicon_teacher"; Description: "Создать ярлык на рабочем столе (Преподаватель)"; GroupDescription: "Дополнительные ярлыки:"; Components: teacher
Name: "desktopicon_student"; Description: "Создать ярлык на рабочем столе (Студент)"; GroupDescription: "Дополнительные ярлыки:"; Components: student

[Files]
; Teacher App
Source: "..\dist\Alfarid_Teacher\*"; DestDir: "{app}\Teacher"; Flags: ignoreversion recursesubdirs createallsubdirs; Components: teacher

; Student App
Source: "..\dist\Alfarid_Student\*"; DestDir: "{app}\Student"; Flags: ignoreversion recursesubdirs createallsubdirs; Components: student

; Backend (опционально)
Source: "..\backend\*"; DestDir: "{app}\Backend"; Flags: ignoreversion recursesubdirs createallsubdirs; Components: backend

; Документация
Source: "..\README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\LICENSE"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\docs\*"; DestDir: "{app}\docs"; Flags: ignoreversion recursesubdirs

[Icons]
Name: "{group}\Alfarid Teacher"; Filename: "{app}\Teacher\Alfarid_Teacher.exe"; Components: teacher
Name: "{group}\Alfarid Student"; Filename: "{app}\Student\Alfarid_Student.exe"; Components: student
Name: "{group}\Документация"; Filename: "{app}\README.md"
Name: "{group}\Удалить Alfarid"; Filename: "{uninstallexe}"

Name: "{autodesktop}\Alfarid Teacher"; Filename: "{app}\Teacher\Alfarid_Teacher.exe"; Tasks: desktopicon_teacher
Name: "{autodesktop}\Alfarid Student"; Filename: "{app}\Student\Alfarid_Student.exe"; Tasks: desktopicon_student

[Run]
Filename: "{app}\Teacher\Alfarid_Teacher.exe"; Description: "Запустить Alfarid Teacher"; Flags: nowait postinstall skipifsilent; Components: teacher
Filename: "{app}\Student\Alfarid_Student.exe"; Description: "Запустить Alfarid Student"; Flags: nowait postinstall skipifsilent; Components: student

[Code]
function InitializeSetup(): Boolean;
begin
  Result := True;
  MsgBox('Добро пожаловать в установку Alfarid!' + #13#10 + 
         'Система дистанционного обучения.' + #13#10#13#10 +
         'Версия: ' + '{#MyAppVersion}', mbInformation, MB_OK);
end;



