#!/usr/bin/bash
# this should be called from within docker to kick off a build
DISABLE_TELEMETRY=1
cd /app
echo ""
echo "============================================"
echo "Installing dependencies"
echo "============================================"
echo ""
wine64 C:\\Python310\\python.exe Z:\\app\\build.windows.py
echo ""
echo "============================================"
echo "Build airunner for windows"
echo "============================================"
echo ""
wine64 C:\\Python310\\python.exe -m PyInstaller --log-level=INFO --noconfirm  Z:\\app\\build.airunner.windows.prod.spec 2>&1 | tee build.log
echo ""
echo "============================================"
echo "Deploying airunner to itch.io"
echo "============================================"
echo ""
chown -R 1000:1000 dist
LATEST_TAG=$(curl -s https://api.github.com/repos/Capsize-Games/airunner/releases/latest | grep tag_name | cut -d '"' -f 4 | sed 's/v//')
echo "Latest tag: $LATEST_TAG"
wget https://dl.itch.ovh/butler/linux-amd64/head/butler && chmod +x butler
./butler push ./dist/airunner capsizegames/ai-runner:windows --userversion $LATEST_TAG