@echo off
setlocal EnableDelayedExpansion

REM Create Desktop\OrbitRx launcher folder
set "REPO=%~dp0.."
if /I "%~1"=="/auto" set "AUTO=1"
if /I "%~1"=="-auto" set "AUTO=1"
if "%~nx0"=="Setup Desktop.bat" set "REPO=%~dp0"
for %%I in ("%REPO%") do set "REPO=%%~fI"

set "DESKTOP=%USERPROFILE%\Desktop\OrbitRx"

echo.
echo  OrbitRx Desktop Setup
echo  ===================
echo  Repo:    %REPO%
echo  Desktop: %DESKTOP%
echo.

if not exist "%REPO%\pyproject.toml" (
    echo ERROR: Could not find pyproject.toml in %REPO%
    echo Run this from the OrbitRx repo root or scripts folder.
    if not defined AUTO pause
    exit /b 1
)

mkdir "%DESKTOP%" 2>nul

(
echo @echo off
echo setlocal
echo set "REPO=%REPO%"
echo cd /d "%%REPO%%"
echo where py ^>nul 2^>^&1 ^&^& set "PY=py" ^|^| set "PY=python"
echo echo Starting OrbitRx Propagation Monitor...
echo "%%PY%%" -m pip show orbitrx ^>nul 2^>^&1
echo if errorlevel 1 ^(
echo     echo OrbitRx is not installed. Run "Install OrbitRx.bat" first.
echo     pause
echo     exit /b 1
echo ^)
echo "%%PY%%" -m orbitrx
echo if errorlevel 1 pause
) > "%DESKTOP%\Run OrbitRx.bat"

(
echo @echo off
echo setlocal
echo set "REPO=%REPO%"
echo cd /d "%%REPO%%"
echo where py ^>nul 2^>^&1 ^&^& set "PY=py" ^|^| set "PY=python"
echo echo Installing OrbitRx and dependencies...
echo "%%PY%%" -m pip install -e ".[full]"
echo if errorlevel 1 ^(
echo     echo Install failed. Install Python 3.11+ from python.org
echo     pause
echo     exit /b 1
echo ^)
echo echo Done! Double-click "Run OrbitRx.bat" to start.
echo pause
) > "%DESKTOP%\Install OrbitRx.bat"

(
echo @echo off
echo set "DATA=%%USERPROFILE%%\.orbitrx"
echo if not exist "%%DATA%%" mkdir "%%DATA%%"
echo start "" "%%DATA%%"
) > "%DESKTOP%\Open Data Folder.bat"

echo Created:
echo   %DESKTOP%\Install OrbitRx.bat
echo   %DESKTOP%\Run OrbitRx.bat
echo   %DESKTOP%\Open Data Folder.bat
echo.

cd /d "%REPO%"
where py >nul 2>&1 && set "PY=py" || set "PY=python"

if defined AUTO (
    echo Installing dependencies automatically...
    "%PY%" -m pip install -e ".[full]"
    if errorlevel 1 (
        echo Install failed.
        pause
        exit /b 1
    )
    echo.
    echo Setup complete! Open your Desktop\OrbitRx folder and double-click "Run OrbitRx.bat".
    timeout /t 5
    explorer "%DESKTOP%"
    exit /b 0
)

set /p DOINSTALL="Install dependencies now? (Y/N): "
if /I "!DOINSTALL!"=="Y" (
    "%PY%" -m pip install -e ".[full]"
    if errorlevel 1 (
        echo Install failed.
        pause
        exit /b 1
    )
    echo Ready! Double-click "Run OrbitRx.bat" on your desktop.
    explorer "%DESKTOP%"
)

echo.
pause
