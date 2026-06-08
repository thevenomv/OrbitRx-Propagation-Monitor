@echo off
echo Building OrbitRx Propagation Monitor...
echo.
echo Installing / upgrading required packages...
pip install -e ".[full,build]" --quiet
echo.
echo Running PyInstaller...
pyinstaller packaging/orbitrx.spec --distpath dist --workpath build
echo.
echo Build complete! Check dist\OrbitRxMonitor.exe
pause
