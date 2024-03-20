#!/usr/bin/bash
# this should be called from within docker to kick off a build
DISABLE_TELEMETRY=1
cd /app
echo ""
echo "============================================"
echo "Installing dependencies"
echo "============================================"
echo ""
python3 /app/dobuild.py
echo ""
echo "============================================"
echo "Build airunner for linux"
echo "============================================"
echo ""
DEV_ENV=0 AIRUNNER_ENVIRONMENT="prod" PYTHONOPTIMIZE=0 python3 -m PyInstaller --log-level=INFO --noconfirm  /app/build.airunner.linux.prod.spec 2>&1 | tee build.log
echo ""
echo "============================================"
echo "Copy timm to dist"
echo "============================================"
echo ""
cp -R /usr/local/lib/python3.10/dist-packages/timm ./dist/airunner/
echo ""
echo "============================================"
echo "Copy libtorch_cuda_linalg.so to dist"
echo "============================================"
echo ""
cp /usr/local/lib/python3.10/dist-packages/torch/lib/libtorch_cuda_linalg.so ./dist/airunner/
echo ""
echo "============================================"
echo "Copy setup.py to dist"
echo "============================================"
echo ""
cp /app/setup.py ./dist/airunner/
echo ""
echo "============================================"
echo "Copy /usr/local/lib/python3.10/dist-packages/Pillow-10.2.0.dist-info to ./dist/airunner/Pillow-10.2.0.dist-info"
echo "============================================"
echo ""
cp -R /usr/local/lib/python3.10/dist-packages/Pillow-10.2.0.dist-info ./dist/airunner/
#echo ""
#echo "============================================"
#echo "Deploying airunner to itch.io"
#echo "============================================"
#echo ""
#chown -R 1000:1000 dist
#LATEST_TAG=$(grep -oP '(?<=version=).*(?=,)' /app/airunner/setup.py | tr -d '"')
#echo "Latest tag: $LATEST_TAG"
#wget https://dl.itch.ovh/butler/linux-amd64/head/butler && chmod +x butler
#./butler push ./dist/airunner capsizegames/ai-runner:ubuntu --userversion $LATEST_TAG