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

alembic_cfg = Config("alembic.ini")
command.upgrade(alembic_cfg, "head")

################################################################
# Run the setup wizard if the application is not yet installed.
################################################################
from airunner.aihandler.models.database_handler import DatabaseHandler
from airunner.aihandler.models.settings_models import ApplicationSettings
from app_installer import AppInstaller
database_handler = DatabaseHandler()
session = database_handler.get_db_session()
application_settings = session.query(ApplicationSettings).first()
session.close()
if application_settings.run_setup_wizard:
    AppInstaller()
    database_handler = DatabaseHandler()
    session = database_handler.get_db_session()
    application_settings = session.query(ApplicationSettings).first()
    session.close()
    if not (
        application_settings.stable_diffusion_agreement_checked and
        application_settings.airunner_agreement_checked and
        application_settings.user_agreement_checked
    ):
        import sys
        sys.exit(0)


if __name__ == "__main__":
    App(
        restrict_os_access=None,
        defendatron=facehuggershield.huggingface.defendatron
    )
