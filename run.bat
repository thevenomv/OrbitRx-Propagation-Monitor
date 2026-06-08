@echo off
cd /d "%~dp0"
echo OrbitRx v5 launcher
echo Folder: %CD%
echo.
python -c "import PySide6; print('PySide6:', PySide6.__version__)" 2>nul || (
    echo Installing dependencies...
    pip install -r requirements.txt
)
if not exist world_map.jpg (
    echo Downloading world map...
    python -c "from orbitrx.paths import ensure_map_image; ensure_map_image()"
)
echo.
echo Starting OrbitRx (Qt UI)...
python app.py
pause
