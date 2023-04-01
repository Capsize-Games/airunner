#!/usr/bin/bash
# this should be called from within docker to kick off a build
DISABLE_TELEMETRY=1
python3 /app/build.py
DEV_ENV=0 AIRUNNER_ENVIRONMENT="prod" PYTHONOPTIMIZE=0 python3 -m PyInstaller --log-level=INFO --noconfirm  /app/build.airunner.linux.prod.spec 2>&1 | tee build.log
chown -R 1000:1000 dist
LATEST_TAG=$(curl -s https://api.github.com/repos/Capsize-Games/airunner/releases/latest | grep tag_name | cut -d '"' -f 4 | sed 's/v//')
wget https://dl.itch.ovh/butler/linux-amd64/head/butler && chmod +x butler
./butler push ./dist/airunner capsizegames/ai-runner:ubuntu --userversion $LATEST_TAG