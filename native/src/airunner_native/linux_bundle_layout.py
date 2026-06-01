"""Helpers for relocatable Linux bundle roots and executable paths."""

from __future__ import annotations

import os
from pathlib import Path
import sys
from dataclasses import dataclass
from typing import Optional


DEFAULT_SYSTEM_PATH = (
    "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
)
KNOWN_VENV_DIRS = {"venv", ".venv"}


@dataclass(frozen=True)
class LinuxBundleLayout:
    """Resolved Linux bundle root and executable locations."""

    bundle_root: Path
    python_executable: Path
    bin_dir: Path

    def daemon_executable(self) -> Optional[Path]:
        """Return the bundled daemon launcher when one exists."""
        candidate = self.bin_dir / "airunner-daemon"
        if candidate.exists():
            return candidate
        return None

    def path_environment(self, current_path: Optional[str] = None) -> str:
        """Return a PATH string preferring this bundle's bin directory."""
        base_path = current_path or os.environ.get("PATH")
        entries = [str(self.bin_dir)]
        if base_path:
            entries.extend(part for part in base_path.split(":") if part)
        else:
            entries.extend(DEFAULT_SYSTEM_PATH.split(":"))
        return ":".join(dict.fromkeys(entries))


def build_linux_bundle_layout(
    bundle_root: Optional[Path | str] = None,
    python_executable: Optional[Path | str] = None,
) -> LinuxBundleLayout:
    """Resolve the active Linux bundle root and Python executable."""
    resolved_bundle_root = _resolve_bundle_root(bundle_root, python_executable)
    resolved_python = _resolve_python_executable(
        resolved_bundle_root,
        python_executable,
    )
    return LinuxBundleLayout(
        bundle_root=resolved_bundle_root,
        python_executable=resolved_python,
        bin_dir=resolved_python.parent,
    )


def _resolve_bundle_root(
    bundle_root: Optional[Path | str],
    python_executable: Optional[Path | str],
) -> Path:
    """Resolve the bundle root from explicit input, env, or Python path."""
    for candidate in (bundle_root, os.environ.get("AIRUNNER_BUNDLE_ROOT")):
        if candidate:
            return Path(candidate).expanduser().resolve()

    inferred = _infer_bundle_root_from_python(
        python_executable or os.environ.get("AIRUNNER_PYTHON")
    )
    if inferred is not None:
        return inferred.resolve()

    return Path.cwd().resolve()


def _resolve_python_executable(
    bundle_root: Path,
    python_executable: Optional[Path | str],
) -> Path:
    """Resolve the Python executable used for this bundle."""
    candidates = [
        python_executable,
        bundle_root / "venv" / "bin" / "python",
        bundle_root / ".venv" / "bin" / "python",
        bundle_root / "bin" / "python",
        os.environ.get("AIRUNNER_PYTHON"),
        Path(sys.executable),
    ]
    for candidate in candidates:
        if not candidate:
            continue
        path = _absolute_path(candidate)
        if path.exists():
            return path
    return _absolute_path(sys.executable)


def _infer_bundle_root_from_python(
    python_executable: Optional[Path | str],
) -> Optional[Path]:
    """Infer the bundle root from common venv-style Python locations."""
    if not python_executable:
        python_path = _absolute_path(sys.executable)
    else:
        python_path = _absolute_path(python_executable)

    if python_path.parent.name != "bin":
        return None

    environment_root = python_path.parent.parent
    if environment_root.name in KNOWN_VENV_DIRS:
        return environment_root.parent.resolve()

    candidate_root = environment_root.resolve()
    if _looks_like_bundle_root(candidate_root):
        return candidate_root
    return None


def _absolute_path(candidate: Path | str) -> Path:
    """Return an absolute path while preserving virtualenv symlink entries."""
    path = Path(candidate).expanduser()
    if path.is_absolute():
        return path
    return (Path.cwd() / path).absolute()


def _looks_like_bundle_root(candidate_root: Path) -> bool:
    """Return True when a directory looks like an AIRunner bundle root."""
    gui_root = candidate_root / "gui" / "src" / "airunner"
    return any(
        (
            (candidate_root / "deployment" / "systemd").exists(),
            gui_root.exists(),
            (
                (candidate_root / "bin" / "airunner-headless").exists()
                and (candidate_root / "bin" / "airunner-daemon").exists()
            ),
        )
    )