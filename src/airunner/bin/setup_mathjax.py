#!/usr/bin/env python3
"""
setup_mathjax.py - Download and extract MathJax 3.x for local use in airunner.

This script checks for MathJax in the static directory and downloads it if missing.
"""
import os
import sys
import urllib.request
import zipfile
# import shutil # No longer needed

# Correct MathJax release asset (contains es5/tex-mml-chtml.js)
MATHJAX_URL = "https://github.com/mathjax/MathJax/releases/download/3.2.2/mathjax-3.2.2.zip"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# STATIC_DIR is intended to be project_root/static/mathjax
# SCRIPT_DIR = project_root/src/airunner/bin
# So, "..", "..", "static", "mathjax" from SCRIPT_DIR should be correct
# ../.. -> src/
# ../../.. -> project_root
# Correct path from SCRIPT_DIR to project_root/static/mathjax:
STATIC_DIR = os.path.abspath(
    os.path.join(SCRIPT_DIR, "..", "..", "..", "static", "mathjax")
)

# The expected entry point relative to STATIC_DIR after extracting the release asset
EXPECTED_MATHJAX_ENTRY_RELATIVE_TO_STATIC_DIR = os.path.join("es5", "tex-mml-chtml.js")
MATHJAX_ENTRY_FULL_PATH = os.path.join(STATIC_DIR, EXPECTED_MATHJAX_ENTRY_RELATIVE_TO_STATIC_DIR)


def ensure_mathjax():
    if os.path.exists(MATHJAX_ENTRY_FULL_PATH):
        print("MathJax already present at:", MATHJAX_ENTRY_FULL_PATH)
        return

    os.makedirs(STATIC_DIR, exist_ok=True)
    temp_zip_path = os.path.join(STATIC_DIR, "mathjax-download.zip")

    print(f"Downloading MathJax from {MATHJAX_URL} to {temp_zip_path}")
    try:
        urllib.request.urlretrieve(MATHJAX_URL, temp_zip_path)
        print("Extracting MathJax...")
        with zipfile.ZipFile(temp_zip_path, "r") as zip_ref:
            # The mathjax-3.2.2.zip release asset should directly contain the 'es5' folder.
            # Extracting all to STATIC_DIR should place 'es5' inside STATIC_DIR.
            zip_ref.extractall(STATIC_DIR)
        print(f"MathJax extracted to: {STATIC_DIR}")
    except Exception as e:
        print(f"Error during download or extraction: {e}")
        # Clean up partially downloaded file if it exists
        if os.path.exists(temp_zip_path):
            os.remove(temp_zip_path)
        sys.exit(1)
    finally:
        # Ensure the temporary zip file is removed
        if os.path.exists(temp_zip_path):
            os.remove(temp_zip_path)

    # Verify that the expected entry file exists
    if not os.path.exists(MATHJAX_ENTRY_FULL_PATH):
        print(f"ERROR: MathJax setup failed. Expected file not found: {MATHJAX_ENTRY_FULL_PATH}")
        print(f"Contents of STATIC_DIR ({STATIC_DIR}):")
        try:
            for item in os.listdir(STATIC_DIR):
                print(f"  - {item}")
        except FileNotFoundError:
            print(f"  ERROR: STATIC_DIR {STATIC_DIR} does not exist or is not accessible.")
        sys.exit(1)
    else:
        print(f"MathJax setup complete. Verified entry file: {MATHJAX_ENTRY_FULL_PATH}")


if __name__ == "__main__":
    try:
        ensure_mathjax()
    except Exception as e:
        print("ERROR: MathJax setup failed:", e)
        sys.exit(1)
