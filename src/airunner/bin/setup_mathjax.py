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

# Correct MathJax release asset (contains es5/tex-mml-chtml.js)
MATHJAX_URL = "https://github.com/mathjax/MathJax/archive/refs/tags/3.2.2.zip"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.abspath(
    os.path.join(SCRIPT_DIR, "..", "..", "static", "mathjax")
)
ZIP_PATH = os.path.join(STATIC_DIR, "mathjax.zip")

# The main entry file for MathJax 3.x CHTML output (after extraction)
MATHJAX_ENTRY = os.path.join(STATIC_DIR, "tex-mml-chtml.js")


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
    # Move es5/* files up to static/mathjax/
    es5_dir = os.path.join(STATIC_DIR, "es5")
    if os.path.isdir(es5_dir):
        for f in os.listdir(es5_dir):
            shutil.move(os.path.join(es5_dir, f), STATIC_DIR)
        shutil.rmtree(es5_dir)
    print("MathJax setup complete at:", STATIC_DIR)


if __name__ == "__main__":
    try:
        ensure_mathjax()
    except Exception as e:
        print("ERROR: MathJax setup failed:", e)
        sys.exit(1)
