@echo off
REM Quick launcher — use setup_desktop.bat once to copy this to your Desktop\OrbitRx folder.
setlocal
set "REPO=%~dp0.."
for %%I in ("%REPO%") do set "REPO=%%~fI"
cd /d "%REPO%"

where py >nul 2>&1 && set "PY=py" || set "PY=python"

"%PY%" -m pip show orbitrx >nul 2>&1
if errorlevel 1 (
    echo OrbitRx not installed. Run: scripts\setup_desktop.bat
    pause
    exit /b 1
)

"%PY%" -m orbitrx
