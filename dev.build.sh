#!/usr/bin/bash
DEV_ENV=0 AIRUNNER_ENVIRONMENT="prod" PYTHONOPTIMIZE=0 python3 -m PyInstaller --log-level=INFO --noconfirm  build.airunner.linux.prod.spec 2>&1 | tee build.log