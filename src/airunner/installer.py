#!/usr/bin/env python

import facehuggershield
facehuggershield.huggingface.activate(
    show_stdout=True,
    darklock_os_whitelisted_operations=[
        "makedirs"
    ]
)
from airunner.app_installer import AppInstaller


if __name__ == "__main__":
    AppInstaller()
