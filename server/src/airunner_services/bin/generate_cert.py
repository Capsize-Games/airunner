"""Generate local development certificates outside the GUI package."""

from __future__ import annotations

from pathlib import Path
import subprocess


def _resolve_script_path() -> Path:
    """Return the packaged certificate helper script path."""
    return Path(__file__).with_name("generate_cert.sh")


def main() -> int:
    """Run the packaged certificate helper script."""
    script_path = _resolve_script_path()
    if not script_path.exists():
        raise FileNotFoundError(
            f"Missing certificate helper script: {script_path}"
        )
    subprocess.run(["bash", str(script_path)], check=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
