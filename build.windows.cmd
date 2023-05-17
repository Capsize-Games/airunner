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
echo "Copy timm to dist"
echo "============================================"
echo.
xcopy /E /I /Y C:\Python310\Lib\site-packages\timm Z:\app\dist\airunner\timm
echo.
echo "============================================"
echo "Copy libtorch_cuda_linalg.so to dist"
echo "============================================"
echo.
xcopy /E /I /Y C:\Python310\Lib\site-packages\torch\lib\libtorch_cuda_linalg.so Z:\app\dist\airunner\libtorch_cuda_linalg.so
echo.
echo "============================================"
echo "Deploying airunner to itch.io"
echo "============================================"
echo.
C:\Python310\python.exe Z:\app\butler.windows.py
