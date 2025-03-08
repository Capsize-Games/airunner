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
from airunner.data.models import WindowSettings
import os
import argparse
base_path = os.path.join(os.path.expanduser("~"), ".local", "share", "airunner")

################################################################
# Set the environment variable for PyTorch to use expandable
################################################################
os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"

################################################################
# Ensure that the base directory exists.
################################################################
base_dir = os.path.join(base_path, "data")
os.makedirs(base_dir, exist_ok=True)

################################################################
# Import the main application class for AI Runner.
################################################################
from airunner.app import App

###############################################################
# Import Alembic modules to run migrations.
################################################################
from alembic.config import Config
from alembic import command
from pathlib import Path
from airunner.data.models import ApplicationSettings


def setup_database():
    base_path = Path(os.path.dirname(os.path.realpath(__file__)))
    alembic_file = base_path / "alembic.ini"
    alembic_dir = base_path / "alembic"
    alembic_cfg = Config(alembic_file)
    alembic_cfg.set_main_option("script_location", str(alembic_dir))
    command.upgrade(alembic_cfg, "head")


def run_setup_wizard():
    from airunner.app_installer import AppInstaller
    AppInstaller()


def main():
    parser = argparse.ArgumentParser(description="AI Runner")
    parser.add_argument("--clear-window-settings", action="store_true", help="Clear window settings")
    args = parser.parse_args()

    if args.clear_window_settings:
        WindowSettings.objects.delete_all()

    setup_database()

    # Get the first ApplicationSettings record from the database and 
    # check for run_setup_wizard boolean
    application_settings = ApplicationSettings.objects.first()
    if not application_settings:
        application_settings = ApplicationSettings()
        application_settings.save()
        application_settings = ApplicationSettings.objects.first()

    if application_settings.run_setup_wizard:
        run_setup_wizard()
    else:
        App()


if __name__ == "__main__":
    main()