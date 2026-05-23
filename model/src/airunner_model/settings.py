"""Model-owned runtime settings."""

from __future__ import annotations

import os


AIRUNNER_BASE_PATH = os.path.expanduser(
    os.environ.get("AIRUNNER_BASE_PATH", "~/.local/share/airunner")
)


__all__ = ["AIRUNNER_BASE_PATH"]