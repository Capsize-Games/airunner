"""
mypy_shortcut.py

Entry point for the 'airunner-mypy' command. Runs mypy against the project's
``[tool.mypy]`` configuration in ``pyproject.toml`` (mypy discovers the config
from the current working directory upward), so ``airunner-mypy <file>`` and a
bare ``mypy <file>`` agree on every flag (issue #2052).

Usage:
    airunner-mypy <filename>
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
        filename,
    ]
    try:
        result = subprocess.run(cmd, check=False)
        sys.exit(result.returncode)
    except KeyboardInterrupt:
        print("Interrupted.", file=sys.stderr)
        sys.exit(1)
