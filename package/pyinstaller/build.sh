#!/usr/bin/bash
# this should be called from within docker to kick off a build

# Ensure the /app/build directory has the correct permissions
if [ ! -d /app/build ]; then
  mkdir -p /app/build
fi
chmod -R 775 /app/build
chown -R $(id -u):$(id -g) /app/build

if [ ! -d /app/dist ]; then
  mkdir -p /app/dist
fi
chmod -R 775 /app/dist
chown -R $(id -u):$(id -g) /app/dist

cd /app

echo ""
echo "============================================"
echo "Build airunner for linux"
echo "============================================"
echo ""
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
LATEST_TAG=$(grep -oP '(?<=version=).*(?=,)' /app/setup.py | tr -d '"')
echo "Latest tag: $LATEST_TAG"
/home/appuser/butler/butler push /app/dist/airunner capsizegames/ai-runner:ubuntu --userversion $LATEST_TAG
