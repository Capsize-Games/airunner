"""Run the AIRunner Docker helper from the service package."""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys


def _resolve_script_path() -> Path:
    """Return the packaged Docker helper script path."""
    return Path(__file__).with_name("docker.sh")


def main() -> int:
    """Run the packaged Docker wrapper shell script."""
    script_path = _resolve_script_path()
    if not script_path.exists():
        raise FileNotFoundError(f"Missing Docker helper script: {script_path}")
    try:
        subprocess.check_call(["/bin/bash", str(script_path), *sys.argv[1:]])
    except subprocess.CalledProcessError as exc:
        return exc.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())