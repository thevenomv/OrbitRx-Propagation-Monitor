@echo off
setlocal EnableDelayedExpansion

REM Create Desktop\OrbitRx launcher folder (run once from the repo)
set "REPO=%~dp0.."
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
    echo Run this script from the scripts folder inside the OrbitRx repo.
    pause
    exit /b 1
)

mkdir "%DESKTOP%" 2>nul

REM --- Run OrbitRx.bat ---
(
echo @echo off
echo setlocal
echo set "REPO=%REPO%"
echo cd /d "%%REPO%%"
echo.
echo REM Prefer Windows Python launcher, fall back to python on PATH
echo where py ^>nul 2^>^&1 ^&^& set "PY=py" ^|^| set "PY=python"
echo.
echo echo Starting OrbitRx Propagation Monitor...
echo "%%PY%%" -m pip show orbitrx ^>nul 2^>^&1
echo if errorlevel 1 ^(
echo     echo.
echo     echo OrbitRx is not installed yet. Run "Install OrbitRx.bat" first.
echo     echo.
echo     pause
echo     exit /b 1
echo ^)
echo.
echo "%%PY%%" -m orbitrx
echo if errorlevel 1 ^(
echo     echo.
echo     echo OrbitRx exited with an error.
echo     pause
echo ^)
) > "%DESKTOP%\Run OrbitRx.bat"

REM --- Install OrbitRx.bat ---
(
echo @echo off
echo setlocal
echo set "REPO=%REPO%"
echo cd /d "%%REPO%%"
echo.
echo where py ^>nul 2^>^&1 ^&^& set "PY=py" ^|^| set "PY=python"
echo.
echo echo Installing OrbitRx and dependencies...
echo echo This may take a minute.
echo "%%PY%%" -m pip install -e ".[full]"
echo if errorlevel 1 ^(
echo     echo.
echo     echo Install failed. Make sure Python 3.11+ is installed from python.org
echo     pause
echo     exit /b 1
echo ^)
echo.
echo echo.
echo echo Done! You can now double-click "Run OrbitRx.bat"
echo pause
) > "%DESKTOP%\Install OrbitRx.bat"

REM --- Open Data Folder.bat ---
(
echo @echo off
echo set "DATA=%%USERPROFILE%%\.orbitrx"
echo if not exist "%%DATA%%" mkdir "%%DATA%%"
echo start "" "%%DATA%%"
) > "%DESKTOP%\Open Data Folder.bat"

echo Created desktop folder with launchers:
echo   %DESKTOP%\Install OrbitRx.bat   ^(run this first^)
echo   %DESKTOP%\Run OrbitRx.bat
echo   %DESKTOP%\Open Data Folder.bat
echo.

set /p DOINSTALL="Install dependencies now? (Y/N): "
if /I "%DOINSTALL%"=="Y" (
    cd /d "%REPO%"
    where py >nul 2>&1 && set "PY=py" || set "PY=python"
    "%PY%" -m pip install -e ".[full]"
    if errorlevel 1 (
        echo Install failed.
        pause
        exit /b 1
    )
    echo.
    echo Ready! Double-click "Run OrbitRx.bat" on your desktop.
) else (
    echo.
    echo Next step: double-click "Install OrbitRx.bat" on your desktop, then "Run OrbitRx.bat".
)

echo.
pause
