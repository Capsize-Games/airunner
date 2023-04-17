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
C:\Python310\python.exe -m PyInstaller --log-level=INFO --noconfirm  Z:\app\airunner\build.airunner.windows.prod.spec 2>&1
echo.
echo "============================================"
echo "Deploying airunner to itch.io"
echo "============================================"
echo.
C:\Python310\python.exe -c "import sys; sys.path.append('Z:\\app\\airunner'); import version; import os; os.system(f'C:\\Python310\\Scripts\\butler.exe push Z:\\app\\dist\\airunner capsizegames/ai-runner:windows --userversion {version.VERSION}')"
