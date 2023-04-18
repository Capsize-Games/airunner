@echo off
cd Z:\app
rem This should be called from within Docker to kick off a build
set DISABLE_TELEMETRY=1
echo.
echo "============================================"
echo "Installing dependencies"
echo "============================================"
echo.
C:\Python310\python.exe Z:\app\build.windows.py
echo.
echo "============================================"
echo "Build airunner for windows"
echo "============================================"
echo.
C:\Python310\python.exe -m PyInstaller --log-level=INFO --noconfirm  Z:\app\build.airunner.windows.prod.spec 2>&1
echo.
echo "============================================"
echo "Deploying airunner to itch.io"
echo "============================================"
echo.
@REM we will set VERSION using the /app/VERSION file contents:
C:\Python310\python.exe -c Z:\app\butler.windows.py
