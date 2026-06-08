; Inno Setup script for OrbitRx Monitor (item 50)
; Build exe first: build.bat
; Then compile this script with Inno Setup 6+

[Setup]
AppName=OrbitRx Propagation Monitor
AppVersion=5.0.0
AppVerName=OrbitRx Monitor 5.0.0
AppPublisher=OrbitRx
AppSupportURL=https://github.com/thevenomv/OrbitRx-Propagation-Monitor
AppUpdatesURL=https://github.com/thevenomv/OrbitRx-Propagation-Monitor/releases
DefaultDirName={autopf}\OrbitRxMonitor
DefaultGroupName=OrbitRx
OutputBaseFilename=OrbitRxMonitor-Setup
Compression=lzma2
SolidCompression=yes
PrivilegesRequired=lowest

[Files]
Source: "..\dist\OrbitRxMonitor.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\world_map.jpg"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\config.json"; DestDir: "{app}"; Flags: onlyifdoesntexist

[Icons]
Name: "{group}\OrbitRx Monitor"; Filename: "{app}\OrbitRxMonitor.exe"
Name: "{autodesktop}\OrbitRx Monitor"; Filename: "{app}\OrbitRxMonitor.exe"

[Run]
Filename: "{app}\OrbitRxMonitor.exe"; Description: "Launch OrbitRx"; Flags: postinstall nowait skipifsilent
