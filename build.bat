@echo off
echo Building OrbitRx Propagation Monitor...
echo.
echo Installing / upgrading required packages...
pip install -r requirements.txt --quiet
echo.
echo Running PyInstaller...
pyinstaller --onefile --windowed ^
  --add-data "world_map.jpg;." ^
  --hidden-import serial ^
  --hidden-import customtkinter ^
  --hidden-import matplotlib ^
  --hidden-import matplotlib.backends.backend_qtagg ^
  --hidden-import PySide6 ^
  --hidden-import win10toast ^
  --hidden-import winsound ^
  --name OrbitRxMonitor ^
  --collect-submodules orbitrx ^
  app.py
echo.
echo Build complete! Check dist\OrbitRxMonitor.exe
pause
