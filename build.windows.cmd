@echo off
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
C:\Python310\python.exe -m PyInstaller --log-level=INFO --noconfirm  Z:\app\build.airunner.windows.prod.spec 2>&1 | tee build.log
echo.
echo "============================================"
echo "Deploying airunner to itch.io"
echo "============================================"
echo.
rem Get the LATEST_TAG from Z:\app\setup.py
for /f "tokens=2 delims==," %%G in ('findstr /r /c:"^version=" Z:\app\setup.py') do set "LATEST_TAG=%%~G"
set "LATEST_TAG=%LATEST_TAG:'=%"
C:\Python310\Scripts\butler.exe push Z:\app\dist\airunner capsizegames/ai-runner:windows --userversion %LATEST_TAG%
