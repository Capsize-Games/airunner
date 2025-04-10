#!/usr/bin/bash
# this should be called from within docker to kick off a build
DISABLE_TELEMETRY=1
cd /app

echo ""
echo "============================================"
echo "Build airunner for linux"
echo "============================================"
echo ""
DEV_ENV=0 AIRUNNER_ENVIRONMENT="prod" PYTHONOPTIMIZE=0 python3 -m PyInstaller --log-level=INFO --noconfirm /app/package/pyinstaller/airunner.spec 2>&1 | tee build.log
echo ""
echo "============================================"
echo "Copy timm to dist"
echo "============================================"
echo ""
cp -R /home/appuser/.local/lib/python3.10/site-packages/timm /app/dist/airunner/
echo ""
echo "============================================"
echo "Copy libtorch_cuda_linalg.so to dist"
echo "============================================"
echo ""
cp /home/appuser/.local/lib/python3.10/site-packages/torch/lib/libtorch_cuda_linalg.so /app/dist/airunner/
echo ""
echo "============================================"
echo "Copy setup.py to dist"
echo "============================================"
echo ""
cp /app/setup.py /app/dist/airunner/
echo ""
echo "============================================"
echo "Copy pillow to dist"
echo "============================================"
echo ""
cp -R /home/appuser/.local/lib/python3.10/site-packages/pillow-10.4.0.dist-info /app/dist/airunner/
echo ""
echo "============================================"
echo "Deploying airunner to itch.io"
echo "============================================"
echo ""
chown -R 1000:1000 dist
LATEST_TAG=$(grep -oP '(?<=version=).*(?=,)' /app/setup.py | tr -d '"')
echo "Latest tag: $LATEST_TAG"
/home/appuser/butler push /app/dist/airunner capsizegames/ai-runner:ubuntu --userversion $LATEST_TAG
