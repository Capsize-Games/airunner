"""
mypy_shortcut.py

Entry point for the 'airunner-mypy' command. Runs mypy with recommended flags for the AI Runner project.

Usage:
    airunner-mypy <filename>

This will run mypy with --ignore-missing-imports and --follow-imports=skip for fast, reliable type checking.
"""

import sys
import subprocess
import os


def main():
    if len(sys.argv) < 2:
        print("Usage: airunner-mypy <filename>", file=sys.stderr)
        sys.exit(1)
    filename = sys.argv[1]
    if not os.path.exists(filename):
        print(f"File not found: {filename}", file=sys.stderr)
        sys.exit(1)
    cmd = [
        sys.executable,
        "-m",
        "mypy",
        "--ignore-missing-imports",
        "--follow-imports=skip",
        filename,
    ]
    try:
        result = subprocess.run(cmd, check=False)
        sys.exit(result.returncode)
    except KeyboardInterrupt:
        print("Interrupted.", file=sys.stderr)
        sys.exit(1)
