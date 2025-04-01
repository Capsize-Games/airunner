#!/usr/bin/env python3
"""
Development runner script for AI Runner.
This script allows developers to run AI Runner directly from the source code,
without needing to build or install it.
"""

import os
import sys
import argparse
from pathlib import Path


def get_project_root():
    """Get the absolute path to the project root directory."""
    current_file = Path(__file__).resolve()
    # Navigate up to the project root (3 levels up from bin)
    return current_file.parent.parent.parent.parent


def main():
    """Run AIRunner in development mode."""
    parser = argparse.ArgumentParser(description="AI Runner development runner")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    args = parser.parse_args()
    
    # Get the project root and add it to the Python path
    root_dir = get_project_root()
    sys.path.insert(0, str(root_dir))
    
    # Set development environment variables
    os.environ["DEV_ENV"] = "1"
    os.environ["AIRUNNER_ENVIRONMENT"] = "dev"
    
    if args.debug:
        os.environ["AIRUNNER_DEBUG"] = "1"
    
    # Import the main module and run it
    from src.airunner.main import main as airunner_main
    airunner_main()


if __name__ == "__main__":
    main()