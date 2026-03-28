@echo off
echo Building OrbitRx Propagation Monitor...
echo.
echo Installing / upgrading required packages...
pip install pillow matplotlib pyserial customtkinter tkcalendar win10toast pyinstaller --quiet
echo.
echo Running PyInstaller...
pyinstaller --onefile --windowed ^
  --add-data "world_map.jpg;." ^
  --hidden-import serial ^
  --hidden-import customtkinter ^
  --hidden-import tkcalendar ^
  --hidden-import matplotlib ^
  --hidden-import win10toast ^
  --hidden-import winsound ^
  --name OrbitRxMonitor app.py
echo.
echo Build complete! Check dist\OrbitRxMonitor.exe
pause
