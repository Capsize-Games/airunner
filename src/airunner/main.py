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
import os
base_path = os.path.join(os.path.expanduser("~"), ".local", "share", "airunner")
facehuggershield.huggingface.activate(
    show_stdout=True,
    darklock_os_whitelisted_directories=[
        base_path,
        NLTK_DOWNLOAD_DIR,
        "/tmp"
    ]
)

################################################################
# Set the environment variable for PyTorch to use expandable
################################################################
os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"

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

def setup_database():
    base_path = Path(os.path.dirname(os.path.realpath(__file__)))
    alembic_file = base_path / "alembic.ini"
    alembic_dir = base_path / "alembic"
    alembic_cfg = Config(alembic_file)
    alembic_cfg.set_main_option("script_location", str(alembic_dir))
    command.upgrade(alembic_cfg, "head")

def main():
    setup_database()
    App(
        defendatron=facehuggershield.huggingface.defendatron
    )


if __name__ == "__main__":
    main()
