from __future__ import annotations

import json
import sys
from pathlib import Path


def _clear_loaded_extensions() -> None:
    # Ensure we re-scan the extensions folder.
    from airunner.components.llm.core import extensions_loader

    setattr(extensions_loader.load_extensions, "_airunner_extensions_loaded", False)

    for name in list(sys.modules.keys()):
        if name == "airunner_extensions" or name.startswith("airunner_extensions."):
            sys.modules.pop(name, None)


def _write_extension(root: Path, *, extension_id: str) -> Path:
    """Create a minimal manifest-driven FastAPI extension package."""
    package_dir = root / "demo_extension"
    package_dir.mkdir(parents=True)
    sentinel = package_dir / "imported.txt"
    sentinel_literal = repr(str(sentinel))
    manifest = {
        "id": extension_id,
        "name": "Demo Extension",
        "version": "1.0.0",
        "kind": "extension",
    }
    (package_dir / "airunner-extension.json").write_text(
        json.dumps(manifest),
        encoding="utf-8",
    )
    (package_dir / "__init__.py").write_text(
        "from pathlib import Path\n"
        "from fastapi import APIRouter\n"
        f"Path({sentinel_literal}).write_text('loaded', encoding='utf-8')\n"
        "router = APIRouter()\n"
        "@router.get('/api/v1/demo/profile')\n"
        "def profile():\n"
        "    return {'status': 'ok'}\n"
        "def register_fastapi(app):\n"
        "    app.include_router(router)\n",
        encoding="utf-8",
    )
    return sentinel


def test_fastapi_skips_external_extensions_by_default(tmp_path, monkeypatch):
    _clear_loaded_extensions()
    sentinel = _write_extension(tmp_path, extension_id="demo.extension")
    monkeypatch.setenv("AIRUNNER_EXTENSIONS_DIR", str(tmp_path))
    monkeypatch.delenv("AIRUNNER_ENABLED_EXTENSIONS", raising=False)

    from airunner.api.server import create_app

    app = create_app(enable_cors=False)

    paths = {getattr(route, "path", None) for route in app.router.routes}

    assert "/api/v1/demo/profile" not in paths
    assert not sentinel.exists()


def test_fastapi_registers_allowlisted_extension_routes(tmp_path, monkeypatch):
    _clear_loaded_extensions()
    sentinel = _write_extension(tmp_path, extension_id="demo.extension")

    monkeypatch.setenv("AIRUNNER_EXTENSIONS_DIR", str(tmp_path))
    monkeypatch.setenv("AIRUNNER_ENABLED_EXTENSIONS", "demo.extension")

    from airunner.api.server import create_app

    app = create_app(enable_cors=False)

    paths = {getattr(route, "path", None) for route in app.router.routes}

    assert "/api/v1/demo/profile" in paths
    assert sentinel.exists()
