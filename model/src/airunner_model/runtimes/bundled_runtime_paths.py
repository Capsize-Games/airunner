"""Resolve bundled native runtime executables from AIRunner bundles."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional


IS_WINDOWS = os.name == "nt"


def resolve_runtime_executable(env_name: str, binary_name: str) -> str:
	"""Return an override, bundled binary, or PATH-based executable."""
	override = os.environ.get(env_name, "").strip()
	if override:
		return os.path.expanduser(override)

	bundled_path = _resolve_bundled_binary(binary_name)
	if bundled_path is not None:
		return str(bundled_path)

	return binary_name


def _resolve_bundled_binary(binary_name: str) -> Optional[Path]:
	"""Return the bundled runtime executable when one exists."""
	bundle_root = os.environ.get("AIRUNNER_BUNDLE_ROOT", "").strip()
	if not bundle_root:
		return None

	resolved_root = Path(os.path.expanduser(bundle_root)).resolve()
	for candidate_name in _candidate_binary_names(binary_name):
		candidate_path = resolved_root / "bin" / candidate_name
		if candidate_path.exists():
			return candidate_path

	return None


def _candidate_binary_names(binary_name: str) -> tuple[str, ...]:
	"""Return platform-appropriate executable name candidates."""
	if IS_WINDOWS:
		return (f"{binary_name}.exe", binary_name)
	return (binary_name, f"{binary_name}.exe")


__all__ = ["IS_WINDOWS", "resolve_runtime_executable"]