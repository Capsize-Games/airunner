#!/usr/bin/env python
"""
Headless server wrapper for AI Runner.

This is a convenience wrapper that starts AI Runner in headless mode.
All the real logic is in App class (app.py) which supports both GUI and headless modes.

Usage:
    python -m airunner.headless_server

Or set environment variable:
    AIRUNNER_HEADLESS=1 python -m airunner.main
"""
import os

# Force headless mode
os.environ["AIRUNNER_HEADLESS"] = "1"

# Import and run main entry point
from airunner.main import main

if __name__ == "__main__":
    main()
