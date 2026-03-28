@echo off
echo Building RadioPropagationTracker.exe...
pyinstaller --onefile --windowed --add-data "world_map.jpg;." --name RadioPropagationTracker app.py
echo Build complete! Check dist folder for executable.
pause
