#!/usr/bin/env python3
"""
setup_mathjax.py - Download and extract MathJax 3.x for local use in airunner.

This script checks for MathJax in the static directory and downloads it if missing.
"""
import os
import sys
import urllib.request
import zipfile
import shutil

from airunner.settings import MATHJAX_VERSION

# Correct MathJax release asset (contains es5/tex-mml-chtml.js)
MATHJAX_URL = f"https://github.com/mathjax/MathJax/archive/refs/tags/{MATHJAX_VERSION}.zip"

# Use MATHJAX_INSTALL_DIR if set (for flatpak), otherwise use package directory
if os.environ.get("MATHJAX_INSTALL_DIR"):
    # MATHJAX_INSTALL_DIR points to the parent of MathJax-{VERSION}
    # e.g., .../static/mathjax (not including MathJax-{VERSION})
    STATIC_DIR = os.environ["MATHJAX_INSTALL_DIR"]
else:
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    STATIC_DIR = os.path.abspath(
        os.path.join(SCRIPT_DIR, "..", "static", "mathjax")
    )
ZIP_PATH = os.path.join(STATIC_DIR, "mathjax.zip")

# The main entry file for MathJax 3.x CHTML output (after extraction)
# The zip extracts to MathJax-{VERSION}/es5/tex-mml-chtml.js
MATHJAX_ENTRY = os.path.join(STATIC_DIR, f"MathJax-{MATHJAX_VERSION}", "es5", "tex-mml-chtml.js")


def ensure_mathjax():
    if os.path.exists(MATHJAX_ENTRY):
        print("MathJax already present at:", MATHJAX_ENTRY)
        return
    os.makedirs(STATIC_DIR, exist_ok=True)
    print("Downloading MathJax from", MATHJAX_URL)
    urllib.request.urlretrieve(MATHJAX_URL, ZIP_PATH)
    print("Extracting MathJax...")
    with zipfile.ZipFile(ZIP_PATH, "r") as zip_ref:
        zip_ref.extractall(STATIC_DIR)
    os.remove(ZIP_PATH)
    # The zip extracts to MathJax-{VERSION}/ which contains es5/
    # No need to move files - the structure is already correct
    print("MathJax setup complete at:", os.path.join(STATIC_DIR, f"MathJax-{MATHJAX_VERSION}"))


if __name__ == "__main__":
    try:
        ensure_mathjax()
    except Exception as e:
        print("ERROR: MathJax setup failed:", e)
        sys.exit(1)
