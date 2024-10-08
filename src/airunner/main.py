#!/usr/bin/env python
"""
----------------------------------------------------------------
Import order is crucial for AI Runner to work as expected.
Do not remove the no_internet_socket import.
Do not change the order of the imports.
----------------------------------------------------------------
"""
################################################################
# Importing this module sets the Hugging Face environment
# variables for the application.
################################################################
import facehuggershield
from airunner.settings import NLTK_DOWNLOAD_DIR
facehuggershield.huggingface.activate(
    show_stdout=True,
    darklock_os_whitelisted_directories=[
        "~/.local/share/airunner",
        NLTK_DOWNLOAD_DIR,
        "/tmp"
    ]
)

################################################################
# Set the environment variable for PyTorch to use expandable
################################################################
import os
os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"

################################################################
# Ensure that the base directory exists.
################################################################
base_dir = os.path.join(os.path.expanduser("~"), ".local", "share", "airunner", "data")
os.makedirs(base_dir, exist_ok=True)

################################################################
# Import the main application class for AI Runner.
################################################################
from airunner.app import App

################################################################
# Import Alembic modules to run migrations.
################################################################
from alembic.config import Config
from alembic import command

def setup_database():
    alembic_cfg = Config("alembic.ini")
    command.upgrade(alembic_cfg, "head")


def main():
    setup_database()
    App(
        restrict_os_access=None,
        defendatron=facehuggershield.huggingface.defendatron
    )


if __name__ == "__main__":
    main()
