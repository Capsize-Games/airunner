"""Runtime extension loader.

Extensions are optional and may live outside the Airrunner repo.

For local development convenience, the loader can load from an `extensions/`
folder adjacent to your checkout (or paths specified via
`AIRUNNER_EXTENSIONS_DIR` / `AIRUNNER_EXTENSIONS_PATH`). Extensions can register
tools via `airunner.components.llm.core.tool_registry.tool`.

Extensions are imported after built-in tools so they can override tools by
registering the same `name`.

Design goals:
- Deterministic load order
- Safe import failures (non-fatal)
- Minimal coupling to the rest of the app
"""

from __future__ import annotations

import os
import sys
import types
import importlib
import importlib.util
from pathlib import Path
from typing import Iterable, List, Optional

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


def load_extensions(force_reload: bool = False) -> dict:
    """Load extensions from `extensions/` folders.

    Returns a dict with load stats.
    """
    # Global guard; extensions should be loaded once per process.
    if getattr(load_extensions, _LOADED_MARKER, False) and not force_reload:
        return {"loaded": 0, "failed": 0, "roots": 0}

    _ensure_parent_package()

    loaded = 0
    failed = 0
    roots = 0
    modules: List[str] = []

    for root in _candidate_extension_dirs():
        if not root.exists() or not root.is_dir():
            continue
        roots += 1
        for pkg_dir in _iter_extension_packages(root):
            module_name = f"airunner_extensions.{pkg_dir.name}"
            init_py = pkg_dir / "__init__.py"

            try:
                if module_name in sys.modules and force_reload:
                    # Some modules loaded from file specs can lack a usable __spec__
                    # for importlib.reload(). In that case, do a clean re-import.
                    try:
                        importlib.reload(sys.modules[module_name])
                        loaded += 1
                        continue
                    except Exception:
                        sys.modules.pop(module_name, None)

                if module_name in sys.modules:
                    # Already imported.
                    continue

                spec = importlib.util.spec_from_file_location(module_name, init_py)
                if spec is None or spec.loader is None:
                    raise RuntimeError(f"Unable to load spec for {init_py}")

                module = importlib.util.module_from_spec(spec)
                sys.modules[module_name] = module
                spec.loader.exec_module(module)  # type: ignore[assignment]
                loaded += 1
                modules.append(module_name)
                logger.info("Loaded extension: %s", module_name)
            except Exception as exc:
                failed += 1
                logger.exception("Failed to load extension %s: %s", module_name, exc)

    setattr(load_extensions, _LOADED_MARKER, True)
    return {"loaded": loaded, "failed": failed, "roots": roots, "modules": modules}
