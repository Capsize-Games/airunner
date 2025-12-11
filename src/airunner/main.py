#!/usr/bin/env python
"""
----------------------------------------------------------------
Import order is crucial for AI Runner to work as expected.
Do not change the order of the imports.
----------------------------------------------------------------
"""
################################################################
# Facehugger Shield is a privacy library that locks down
# file system, network and log operations.
# Keep this at the top of the main file.
################################################################
from airunner.settings import AIRUNNER_DISABLE_FACEHUGGERSHIELD
import os
import sys

# Prevent Qt WebEngine from crashing
os.environ["QT_QUICK_BACKEND"] = "software"
os.environ["QT_XCB_GL_INTEGRATION"] = "none"
os.environ["TOKENIZERS_PARALLELISM"] = "true"

# Set fontconfig path to avoid "Cannot load default config file" errors
# This helps Qt WebEngine find font configuration
if not os.environ.get("FONTCONFIG_PATH"):
    fontconfig_paths = [
        "/etc/fonts",
        "/usr/share/fontconfig",
        os.path.join(os.path.expanduser("~"), ".config", "fontconfig"),
    ]
    for path in fontconfig_paths:
        if os.path.isdir(path):
            os.environ["FONTCONFIG_PATH"] = path
            break

"""
Temporary fix for windows - Facehuggershield is not working correctly
on windows at this time so we disable it.
"""
if not AIRUNNER_DISABLE_FACEHUGGERSHIELD:
    from airunner.vendor.facehuggershield.huggingface import activate

    airunner_path = os.path.join(
        os.path.expanduser("~"), ".local", "share", "airunner"
    )
    # Determine site-packages path dynamically
    venv_path = os.path.dirname(os.path.dirname(sys.executable))
    site_packages_path = os.path.join(
        venv_path,
        "lib",
        f"python{sys.version_info.major}.{sys.version_info.minor}",
        "site-packages",
    )
    # Determine project root and src/airunner path
    project_root = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..")
    )
    airunner_src_path = os.path.join(project_root, "src", "airunner")
    airunner_egg_info_path = os.path.join(
        project_root, "src", "airunner.egg-info"
    )

    activate(
        activate_shadowlogger=True,
        darklock_os_allow_network=True,  # Allow network access for downloads
        darklock_os_whitelisted_operations=["makedirs", "mkdir", "open"],
        darklock_os_whitelisted_directories=[
            airunner_path,
            os.path.join(airunner_path, "cache"),  # Web content cache
            os.path.join(airunner_path, "cache/.webcache"),  # Web scraper cache
            os.path.join(airunner_path, "code"),  # Code generation workspace
            os.path.join(airunner_path, "data"),
            os.path.join(airunner_path, "static"),  # Static assets (MathJax, etc.)
            os.path.join(airunner_path, "text"),
            os.path.join(airunner_path, "text/other"),
            os.path.join(airunner_path, "text/other/documents"),
            os.path.join(airunner_path, "text/other/ebooks"),
            os.path.join(airunner_path, "text/other/research"),
            os.path.join(airunner_path, "text/other/webpages"),
            os.path.join(airunner_path, "text/models"),
            os.path.join(airunner_path, "text/rag"),
            os.path.join(airunner_path, "art"),
            os.path.join(airunner_path, "art/models"),
            os.path.join(airunner_path, "art/other"),
            os.path.join(airunner_path, "art/other/images"),
            os.path.join(airunner_path, "certs"),
            os.path.join(os.path.expanduser("~"), ".triton/cache/"),
            os.path.join(os.path.expanduser("~"), ".cache/llama_index/"),
            os.path.join(os.path.expanduser("~"), "Desktop/"),
            "/dev/",
            "/proc/",
            site_packages_path,
            "/usr/share/zoneinfo/",
            airunner_src_path,
            airunner_egg_info_path,
            "/tmp/",
            "/etc/",
            "/var/log/airunner/",  # Add headless server log directory
            os.path.join(os.path.expanduser("~"), "nltk_data/"),
            os.path.join(
                os.path.expanduser("~"), "nltk_data/corpora/stopwords/english"
            ),
            os.path.join(
                os.path.expanduser("~"), "nltk_data/corpora/stopwords/"
            ),
            os.path.join(os.path.expanduser("~"), "nltk_data/corpora/"),
            os.path.join(
                os.path.expanduser("~"), "nltk_data/corpora/stopwords"
            ),
            os.path.join(os.path.expanduser("~"), "nltk_data"),
            os.path.join(os.path.expanduser("~"), "nltk_data/corpora"),
        ],
        nullscream_whitelist=[
            "transformers",
            "diffusers",
            "sentencepiece",
        ],
        nullscream_blacklist=[
            "huggingface_hub",
            "google.cloud.storage",
        ],
    )
#################################################################

os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"

# Initialize the logger
import logging


# Optimize logger initialization by consolidating configurations
def initialize_loggers():
    loggers_to_silence = [
        "torio._extension.utils",
        "google.cloud.storage._opentelemetry_tracing",
        "numba",
        "h5py._conv",
        "matplotlib",
        "datasets",
        "bitsandbytes",
        "trafilatura",
        "scrapy",
        "rquest",
        "primp",
        "cookie_store",
    ]
    for logger_name in loggers_to_silence:
        logging.getLogger(logger_name).setLevel(logging.WARNING)


# Call the consolidated logger initialization
initialize_loggers()

import sys
from airunner.settings import AIRUNNER_LOG_FILE, AIRUNNER_SAVE_LOG_TO_FILE
import argparse
from airunner.utils.settings.get_qsettings import get_qsettings

base_path = os.path.join(
    os.path.expanduser("~"), ".local", "share", "airunner"
)

################################################################
# Ensure that the base directory exists.
################################################################
base_dir = os.path.join(base_path, "data")
try:
    os.makedirs(base_dir, exist_ok=True)
except FileExistsError:
    pass

DEV_ENV = os.environ.get("DEV_ENV", "1") == "1"
if AIRUNNER_SAVE_LOG_TO_FILE and not DEV_ENV:
    try:
        os.makedirs(
            os.path.dirname(os.path.expanduser(AIRUNNER_LOG_FILE)),
            exist_ok=True,
        )
        sys.stdout = open(AIRUNNER_LOG_FILE, "a")
        sys.stderr = open(AIRUNNER_LOG_FILE, "a")
    except PermissionError:
        # Fall back to /tmp if we don't have permissions to write the desired file
        fallback = os.path.join("/tmp", "airunner.log")
        try:
            sys.stdout = open(fallback, "a")
            sys.stderr = open(fallback, "a")
        except Exception:
            # If this still fails, keep default stdout/stderr and continue
            pass
    except Exception:
        # Any other unexpected error: don't crash the startup
        pass

################################################################
# Set the environment variable for PyTorch to use expandable
################################################################
import torch

torch.hub.set_dir(
    os.environ.get(
        "TORCH_HOME",
        os.path.join(
            os.path.expanduser("~"), ".local/share/airunner/torch/hub"
        ),
    )
)

################################################################
# Import the main application class for AI Runner.
################################################################
from airunner.components.application.api.api import API

###############################################################
# Import Alembic modules to run migrations.
################################################################
from airunner.setup_database import setup_database

# These may be set by launcher.py for early splash screen
_launcher_splash = None
_launcher_app = None


def main():
    global _launcher_splash, _launcher_app
    
    parser = argparse.ArgumentParser(description="AI Runner")
    parser.add_argument(
        "--clear-window-settings",
        action="store_true",
        help="Clear window settings",
    )
    parser.add_argument(
        "--print-llm-system-prompt",
        action="store_true",
        help="Print LLM System prompt to console",
    )
    parser.add_argument(
        "--perform-llm-analysis",
        action="store_true",
        help="Perform LLM analysis",
    )
    parser.add_argument(
        "--chatbot-only", action="store_true", help="Run LLM only"
    )
    parser.add_argument(
        "--watch",
        action="store_true",
        help="Watch .ui files and live-reload the app on changes (development only)",
    )
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

    if args.watch:
        # Handled in launcher.py, but keep for help output and future use
        pass

    setup_database()

    # Configure headless logging early, before API/App instantiation
    # This ensures root logger is configured before service loggers are created
    sys.stderr.write("DEBUG: main.py starting\n")

    # Start the main application, passing launcher's splash if available
    api = API(launcher_splash=_launcher_splash, launcher_app=_launcher_app)
    api.run()


if __name__ == "__main__":
    main()
