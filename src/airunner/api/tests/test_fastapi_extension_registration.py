from __future__ import annotations

import sys
from pathlib import Path


def _repo_root_from(start: Path) -> Path:
    current = start
    for _ in range(12):
        if (current / "pyproject.toml").exists() or (current / "setup.py").exists():
            return current
        if current.parent == current:
            break
        current = current.parent
    raise RuntimeError("Unable to locate repo root")


def _clear_loaded_extensions() -> None:
    # Ensure we re-scan the extensions folder.
    from airunner.components.llm.core import extensions_loader

    setattr(extensions_loader.load_extensions, "_airunner_extensions_loaded", False)

    for name in list(sys.modules.keys()):
        if name == "airunner_extensions" or name.startswith("airunner_extensions."):
            sys.modules.pop(name, None)


def test_fastapi_registers_uwuchat_extension_routes(monkeypatch):
    from airunner.components.llm.core import extensions_loader

    repo_root = _repo_root_from(Path(extensions_loader.__file__).resolve())
    monkeypatch.setenv("AIRUNNER_EXTENSIONS_DIR", str(repo_root / "extensions"))

    _clear_loaded_extensions()

    from airunner.api.server import create_app

    app = create_app(enable_cors=False)

    paths = {getattr(r, "path", None) for r in app.router.routes}

    assert "/api/v1/uwuchat/profile" in paths
