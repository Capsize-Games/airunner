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
import os
import argparse
from airunner.utils.settings import get_qsettings
base_path = os.path.join(os.path.expanduser("~"), ".local", "share", "airunner")



################################################################
# Set the environment variable for PyTorch to use expandable
################################################################
os.environ['TORCH_HOME'] = '/home/joe/Projects/airunner/venv/lib/python3.10/site-packages/torch/hub/'
os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"

import torch
torch.hub.set_dir('/home/joe/Projects/airunner/venv/lib/python3.10/site-packages/torch/hub/')

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
    base = Path(os.path.dirname(os.path.realpath(__file__)))
    alembic_file = base / "alembic.ini"
    alembic_dir = base / "alembic"
    alembic_cfg = Config(alembic_file)
    alembic_cfg.set_main_option("script_location", str(alembic_dir))
    command.upgrade(alembic_cfg, "head")


def run_setup_wizard():
    from airunner.app_installer import AppInstaller
    AppInstaller()


def main():
    parser = argparse.ArgumentParser(description="AI Runner")
    parser.add_argument("--clear-window-settings", action="store_true", help="Clear window settings")
    parser.add_argument("--print-llm-system-prompt", action="store_true", help="Print LLM System prompt to console")
    parser.add_argument("--perform-llm-analysis", action="store_true", help="Perform LLM analysis")
    parser.add_argument("--chatbot-only", action="store_true", help="Run LLM only")
    args = parser.parse_args()

    if args.clear_window_settings:
        # Clear all window settings from QSettings
        settings = get_qsettings()
        settings.beginGroup("splitters")
        settings.remove("")  # Removes all keys under the "splitters" group
        settings.endGroup()
    
    if args.print_llm_system_prompt:
        os.environ["AIRUNNER_LLM_PRINT_SYSTEM_PROMPT"] = "1"
    
    if args.perform_llm_analysis:
        os.environ["AIRUNNER_LLM_PERFORM_ANALYSIS"] = "1"
    
    if args.chatbot_only:
        os.environ["AIRUNNER_ART_ENABLED"] = "0"
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
