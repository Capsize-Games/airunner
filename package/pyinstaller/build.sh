#!/usr/bin/bash
# this should be called from within docker to kick off a build
DEV_ENV=0
DISABLE_TELEMETRY=1
AIRUNNER_LLM_USE_LOCAL=1
AIRUNNER_SAVE_LOG_TO_FILE=0
AIRUNNER_LOG_LEVEL=WARNING
AIRUNNER_DISABLE_FACEHUGGERSHIELD=1
AIRUNNER_LLM_USE_OPENROUTER=0
OPENROUTER_API_KEY=""
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
/home/appuser/butler push /app/dist/airunner capsizegames/ai-runner:ubuntu --userversion $LATEST_TAG
