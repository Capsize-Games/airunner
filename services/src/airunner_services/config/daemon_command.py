"""Daemon process entry points for Python and frozen service images."""

from __future__ import annotations

from pathlib import Path
import sys


def daemon_module_command(python_executable: str | Path) -> list[str]:
    """Launch a frozen daemon image directly, or a Python daemon module.

    A frozen executable is not a Python interpreter. Resolve its console
    symlink so a supervisor alias does not recursively launch itself.
    Preserve virtual-environment symlinks for ordinary Python execution.
    """
    if getattr(sys, "frozen", False):
        return [str(Path(sys.executable).resolve())]
    return [str(python_executable), "-m", "airunner_services.daemon"]
