; VideoDevour Windows 安装包配置（Inno Setup 6）
;
; 构建：iscc.exe desktop\installer.iss
; 前置：已执行 desktop\build_win.ps1 生成 desktop\dist\VideoDevour\
;
; 设计说明：
; - 安装到 %LOCALAPPDATA%\Programs\VideoDevour（免管理员权限）
; - 用户数据在 %LOCALAPPDATA%\VideoDevour，卸载时保留（方案 6.3：升级与卸载保留资料）
; - 不对可执行文件做数字签名时，SmartScreen 会提示，属预期行为

#define AppName "VideoDevour"
#define AppVersion "0.1.0"
#define AppPublisher "VideoDevour"
#define AppExeName "VideoDevour.exe"

[Setup]
AppId={{8F3A2C41-5D6E-4B92-9A17-3C4E5F6A7B80}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={localappdata}\Programs\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=dist
OutputBaseFilename={#AppName}-{#AppVersion}-setup
Compression=lzma2/max
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64compatible
WizardStyle=modern
; 卸载时不删除用户数据目录（任务、报告、设置保留）

[Languages]
Name: "chinesesimplified"; MessagesFile: "compiler:Languages\ChineseSimplified.isl"

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"; GroupDescription: "附加任务:"

[Files]
; onedir 产物整体复制
Source: "dist\{#AppName}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExeName}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExeName}"; Description: "启动 {#AppName}"; Flags: nowait postinstall skipifsilent
