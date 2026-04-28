"""Runtime extension loader for explicitly enabled external extensions."""

from __future__ import annotations

import os
import sys
import types
import importlib.util
from pathlib import Path
from typing import Iterable, List, Optional

from airunner.extension_manifest import (
    EXTENSION_ALLOWLIST_ENV,
    load_enabled_extension_ids,
    resolve_enabled_manifest,
)
from airunner.utils.application import get_logger


logger = get_logger(__name__)


_LOADED_MARKER = "_airunner_extensions_loaded"


def _find_repo_root(start: Path) -> Optional[Path]:
    current = start
    for _ in range(12):
        if (current / "pyproject.toml").exists() or (current / "setup.py").exists():
            return current
        if current.parent == current:
            break
        current = current.parent
    return None


def _candidate_extension_dirs() -> List[Path]:
    candidates: List[Path] = []

    env_value = os.environ.get("AIRUNNER_EXTENSIONS_DIR") or os.environ.get(
        "AIRUNNER_EXTENSIONS_PATH"
    )
    if env_value:
        for part in env_value.split(os.pathsep):
            part = part.strip()
            if not part:
                continue
            candidates.append(Path(part).expanduser())

    # Prefer a local adjacent extensions/ folder (convenience-only).
    repo_root = _find_repo_root(Path(__file__).resolve())
    if repo_root is not None:
        candidates.append(repo_root / "extensions")

    # Also allow a workspace-root extensions/ when running from elsewhere.
    try:
        candidates.append(Path.cwd() / "extensions")
    except Exception:
        pass

    # De-dup while preserving order.
    unique: List[Path] = []
    seen: set[str] = set()
    for p in candidates:
        key = str(p.resolve()) if p.exists() else str(p)
        if key in seen:
            continue
        seen.add(key)
        unique.append(p)
    return unique


def _iter_extension_packages(extension_root: Path) -> Iterable[Path]:
    if not extension_root.exists() or not extension_root.is_dir():
        return []

    children = [p for p in extension_root.iterdir() if p.is_dir()]
    children.sort(key=lambda p: p.name.lower())

    packages: List[Path] = []
    for child in children:
        if child.name.startswith(".") or child.name.startswith("_"):
            continue
        init_py = child / "__init__.py"
        if init_py.exists():
            packages.append(child)
    return packages


def _ensure_parent_package() -> None:
    """Create a stable parent namespace for loaded extensions."""
    if "airunner_extensions" in sys.modules:
        return
    pkg = types.ModuleType("airunner_extensions")
    pkg.__path__ = []  # type: ignore[attr-defined]
    sys.modules["airunner_extensions"] = pkg


def _clear_loaded_extension_modules() -> None:
    """Drop previously imported extension modules before a forced reload."""
    for name in list(sys.modules.keys()):
        if name.startswith("airunner_extensions."):
            sys.modules.pop(name, None)


def _iter_enabled_manifests(
    extension_root: Path,
    enabled_ids: set[str],
) -> Iterable:
    """Yield validated manifests for explicitly enabled extensions."""
    for pkg_dir in _iter_extension_packages(extension_root):
        manifest = resolve_enabled_manifest(
            pkg_dir,
            default_entry_point="__init__.py",
            enabled_ids=enabled_ids,
            expected_kind="extension",
        )
        if manifest is not None:
            yield manifest


def _load_extension_module(manifest) -> Optional[str]:
    """Import one external extension module."""
    module_name = f"airunner_extensions.{manifest.module_name}"
    spec = importlib.util.spec_from_file_location(
        module_name,
        manifest.entry_path,
        submodule_search_locations=[str(manifest.entry_path.parent)],
    )
    if spec is None or spec.loader is None:
        logger.warning("Unable to create spec for %s", manifest.entry_path)
        return None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)  # type: ignore[assignment]
    except Exception as exc:
        sys.modules.pop(module_name, None)
        logger.exception("Failed to load extension %s: %s", module_name, exc)
        return None
    logger.info("Loaded extension: %s", module_name)
    return module_name


def _load_root_extensions(
    extension_root: Path,
    enabled_ids: set[str],
) -> dict:
    """Load enabled extensions from a single root directory."""
    loaded = 0
    failed = 0
    modules: List[str] = []
    for manifest in _iter_enabled_manifests(extension_root, enabled_ids):
        module_name = _load_extension_module(manifest)
        if module_name is None:
            failed += 1
            continue
        loaded += 1
        modules.append(module_name)
    return {"loaded": loaded, "failed": failed, "modules": modules}


def load_extensions(force_reload: bool = False) -> dict:
    """Load extensions from `extensions/` folders.

    Returns a dict with load stats.
    """
    if getattr(load_extensions, _LOADED_MARKER, False) and not force_reload:
        return {"loaded": 0, "failed": 0, "roots": 0}

    if force_reload:
        _clear_loaded_extension_modules()

    enabled_ids = load_enabled_extension_ids(EXTENSION_ALLOWLIST_ENV)
    if not enabled_ids:
        return {"loaded": 0, "failed": 0, "roots": 0, "modules": []}

    _ensure_parent_package()

    loaded = 0
    failed = 0
    roots = 0
    modules: List[str] = []

    for root in _candidate_extension_dirs():
        if not root.exists() or not root.is_dir():
            continue
        roots += 1
        result = _load_root_extensions(root, enabled_ids)
        loaded += result["loaded"]
        failed += result["failed"]
        modules.extend(result["modules"])

    setattr(load_extensions, _LOADED_MARKER, True)
    return {"loaded": loaded, "failed": failed, "roots": roots, "modules": modules}
