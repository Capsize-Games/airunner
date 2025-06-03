"""
Alembic migration generator for AI Runner.

This script provides a CLI for generating Alembic migrations using autogenerate.
"""

import sys
import subprocess
from pathlib import Path


def main() -> None:
    """Generate an Alembic migration with the provided message.

    Usage:
        airunner-generate-migration "your migration message"
    """
    if len(sys.argv) < 2:
        print('Usage: airunner-generate-migration "your migration message"')
        sys.exit(1)

    message = sys.argv[1]
    alembic_ini = Path(__file__).parent.parent / "alembic.ini"
    if not alembic_ini.exists():
        print(f"Could not find alembic.ini at {alembic_ini}")
        sys.exit(1)

    cmd = [
        sys.executable,
        "-m",
        "alembic",
        "-c",
        str(alembic_ini),
        "revision",
        "--autogenerate",
        "-m",
        message,
    ]
    result = subprocess.run(cmd)
    sys.exit(result.returncode)
