@echo off
cd Z:\app
rem This should be called from within Docker to kick off a build
set DISABLE_TELEMETRY=1
echo.
echo "============================================"
echo "Installing dependencies"
echo "============================================"
echo.
C:\Python310\python.exe Z:\app\airunner\build.windows.py
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
C:\Python310\python.exe -c "import sys; sys.path.append('Z:\\app'); import version; open('Z:\\app\\dist\\VERSION', 'w').write(version.VERSION)"
