"""All distribution builds must honor the same unpublished candidate version."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_SETUP_FILES = (
    _PROJECT_ROOT / "setup.py",
    _PROJECT_ROOT / "services" / "setup.py",
    _PROJECT_ROOT / "native" / "setup.py",
)


def test_candidate_version_override_is_used_by_every_distribution() -> None:
    env = os.environ.copy()
    env["AIRUNNER_BUILD_VERSION"] = "6.1.3+candidate1"

    for setup_file in _SETUP_FILES:
        result = subprocess.run(
            [sys.executable, str(setup_file), "--version"],
            cwd=setup_file.parent,
            env=env,
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )
        assert result.returncode == 0, result.stderr
        assert result.stdout.strip().endswith("6.1.3+candidate1")

