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

# Skip Butler deployment when SKIP_BUTLER environment variable is set
if [ "${SKIP_BUTLER}" = "1" ]; then
    echo "============================================"
    echo "Skipping Butler deployment (SKIP_BUTLER=1)"
    echo "============================================"
else
    echo "============================================"
    echo "Deploying airunner to itch.io"
    echo "============================================"
    echo ""
    chown -R 1000:1000 dist
    LATEST_TAG=$(grep -oP '(?<=version=).*(?=,)' /app/setup.py | tr -d '"')
    echo "Latest tag: $LATEST_TAG"
    /home/appuser/butler/butler push /app/dist/airunner capsizegames/ai-runner:ubuntu_50xx --userversion $LATEST_TAG
fi
