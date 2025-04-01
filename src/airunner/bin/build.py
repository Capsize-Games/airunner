#!/usr/bin/env python3
"""
Local build script for AI Runner.
This script allows developers to build AI Runner locally for testing
without triggering deployments to itch.io.
"""

import os
import argparse
import platform
import subprocess
import sys
from pathlib import Path


def run_command(cmd, cwd=None):
    """Run a shell command and print output."""
    print(f"Running: {cmd}")
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        shell=True,
        universal_newlines=True,
        cwd=cwd
    )
    
    for line in process.stdout:
        print(line, end='')
    
    process.wait()
    if process.returncode != 0:
        print(f"Command failed with exit code {process.returncode}")
        sys.exit(process.returncode)


def get_project_root():
    """Get the absolute path to the project root directory."""
    current_file = Path(__file__).resolve()
    # Navigate up to the project root (3 levels up from bin)
    return current_file.parent.parent.parent.parent


def build_package(args):
    """Build the Python package."""
    root_dir = get_project_root()
    os.chdir(root_dir)
    
    # Build the Python package
    run_command("python -m build")
    
    # Install the package in development mode
    run_command("pip install -e .")


def build_executable(args):
    """Build the executable using PyInstaller."""
    root_dir = get_project_root()
    os.chdir(root_dir)
    
    spec_file = os.path.join(root_dir, "package", "airunner.spec")
    
    # Set environment variables for the build
    os.environ["DEV_ENV"] = "0"
    os.environ["AIRUNNER_ENVIRONMENT"] = "dev" if args.dev else "prod"
    os.environ["PYTHONOPTIMIZE"] = "0"
    
    # Determine the OS
    current_os = platform.system().lower()
    os.environ["AIRUNNER_OS"] = current_os
    
    # Build using PyInstaller
    cmd = f"pyinstaller --log-level=INFO --noconfirm {spec_file}"
    run_command(cmd)
    
    print(f"\nBuild completed successfully!")
    print(f"Executable can be found in: {os.path.join(root_dir, 'dist', 'airunner')}")


def main():
    parser = argparse.ArgumentParser(description="AI Runner local build tool")
    subparsers = parser.add_subparsers(dest="command", help="Build command")
    
    # Package builder
    pkg_parser = subparsers.add_parser("package", help="Build Python package")
    
    # Executable builder
    exe_parser = subparsers.add_parser("exe", help="Build executable")
    exe_parser.add_argument("--dev", action="store_true", help="Build in development mode")
    
    args = parser.parse_args()
    
    if args.command == "package":
        build_package(args)
    elif args.command == "exe":
        build_executable(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()