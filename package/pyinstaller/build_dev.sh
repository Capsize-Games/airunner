#!/usr/bin/bash
cd /app
echo "============================================"
echo "Build airunner for linux"
echo "============================================"
echo ""
echo "Running PyInstaller"
DEV_ENV=0 AIRUNNER_ENVIRONMENT="prod" PYTHONOPTIMIZE=0 python3 -m PyInstaller --log-level=INFO --noconfirm /app/package/pyinstaller/airunner.spec 2>&1 | tee build.log
echo ""
echo "============================================"
echo "Copy setup.py to dist"
echo "============================================"
echo ""
cp /app/setup.py /app/dist/airunner/_internal/airunner/
echo ""
echo "============================================"
echo "Deploying airunner to itch.io"
echo "============================================"
echo ""
chown -R 1000:1000 dist