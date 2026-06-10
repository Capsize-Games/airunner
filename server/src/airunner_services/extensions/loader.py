"""Extension discovery and hook application.

The loader reads the ``EXTENSIONS`` setting to discover enabled
extensions, imports their ``ExtensionConfig`` subclass, and applies
server-side hooks (routes, middleware, models, migrations) to the
FastAPI application and database setup.
"""

from __future__ import annotations

import importlib
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI

from airunner_services.conf import settings
from airunner_services.extensions.config import ExtensionConfig

_loaded_extensions: dict[str, ExtensionConfig] = {}
_loader_instance: Optional["ExtensionLoader"] = None


class ExtensionLoader:
    """Discovers, loads, and applies configured extensions."""

    def __init__(self) -> None:
        self.configs: dict[str, ExtensionConfig] = {}

    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------
    def load(self) -> dict[str, ExtensionConfig]:
        """Import all configured extensions and return their configs."""
        for path in settings.EXTENSIONS:
            if not path:
                continue
            try:
                mod = importlib.import_module(str(path))
                config = self._extract_config(mod)
                if config is not None:
                    self.configs[config.name] = config
            except ModuleNotFoundError:
                pass  # Extension is optional; skip silently
        return self.configs

    @staticmethod
    def _extract_config(module: Any) -> Optional[ExtensionConfig]:
        """Find the ``ExtensionConfig`` subclass in one module."""
        for attr_name in dir(module):
            attr = getattr(module, attr_name, None)
            if (
                isinstance(attr, type)
                and issubclass(attr, ExtensionConfig)
                and attr is not ExtensionConfig
            ):
                try:
                    return attr()
                except Exception:
                    pass
        return None

    # ------------------------------------------------------------------
    # Server-side hook application
    # ------------------------------------------------------------------
    def apply_server_hooks(self, app: FastAPI) -> None:
        """Register all extension hooks on a FastAPI application."""
        for config in self.configs.values():
            self._register_routes(app, config)
            self._register_middleware(app, config)
            self._call_ready(config)

    @staticmethod
    def _register_routes(app: FastAPI, config: ExtensionConfig) -> None:
        """Auto-discover and register one extension's FastAPI router."""
        module_path = (
            config.server_routes_module
            or f"extensions.{config.name}.server.routes"
        )
        try:
            mod = importlib.import_module(module_path)
            router = getattr(mod, "router", None)
            if router is not None:
                prefix = f"/api/v1/{config.name}"
                tags = [config.label or config.name]
                app.include_router(router, prefix=prefix, tags=tags)
        except ModuleNotFoundError:
            pass  # Routes are optional

    @staticmethod
    def _register_middleware(app: FastAPI, config: ExtensionConfig) -> None:
        """Auto-discover and register one extension's middleware."""
        module_path = (
            config.server_middleware_module
            or f"extensions.{config.name}.server.middleware"
        )
        try:
            mod = importlib.import_module(module_path)
            register_fn = getattr(mod, "register", None)
            if register_fn is not None:
                register_fn(app)
        except ModuleNotFoundError:
            pass  # Middleware is optional

    @staticmethod
    def _call_ready(config: ExtensionConfig) -> None:
        """Call the extension's ready() hook."""
        try:
            config.ready()
        except Exception:
            pass  # Never let an extension break startup

    # ------------------------------------------------------------------
    # Model / Migration discovery (used by setup_database)
    # ------------------------------------------------------------------
    def get_models(self) -> list[type]:
        """Return all SQLAlchemy models from loaded extensions."""
        models: list[type] = []
        for config in self.configs.values():
            module_path = (
                config.server_models_module
                or f"extensions.{config.name}.server.models"
            )
            try:
                mod = importlib.import_module(module_path)
                for attr_name in dir(mod):
                    attr = getattr(mod, attr_name, None)
                    if isinstance(attr, type) and hasattr(
                        attr, "__tablename__"
                    ):
                        models.append(attr)
            except ModuleNotFoundError:
                pass
        return models

    def get_migration_paths(self) -> list[Path]:
        """Return Alembic migration directories from loaded extensions.

        Each path points to a directory containing a ``versions/``
        subdirectory, suitable for appending to Alembic's
        ``version_locations``.

        The location is derived from each extension's *actually imported*
        package (``extensions.{name}``) rather than a guessed relative
        path, so it works no matter where the extensions repo lives on
        disk relative to the core package.
        """
        paths: list[Path] = []
        for config in self.configs.values():
            try:
                pkg = importlib.import_module(f"extensions.{config.name}")
            except ModuleNotFoundError:
                continue
            pkg_file = getattr(pkg, "__file__", None)
            if not pkg_file:
                continue
            candidate = (
                Path(pkg_file).resolve().parent / "server" / "migrations"
            )
            versions_dir = candidate / "versions"
            if versions_dir.is_dir():
                paths.append(candidate)
        return paths


# ------------------------------------------------------------------
# Module-level convenience API
# ------------------------------------------------------------------
def get_loader() -> ExtensionLoader:
    """Return the singleton extension loader (lazily initialised)."""
    global _loader_instance  # noqa: PLW0603
    if _loader_instance is None:
        _loader_instance = ExtensionLoader()
    return _loader_instance


def load_extensions() -> dict[str, ExtensionConfig]:
    """Convenience: import all configured extensions."""
    loader = get_loader()
    return loader.load()


def apply_server_hooks(app: FastAPI) -> None:
    """Convenience: apply all extension hooks to a FastAPI app."""
    loader = get_loader()
    loader.apply_server_hooks(app)


def get_extension_models() -> list[type]:
    """Convenience: return all extension SQLAlchemy models."""
    return get_loader().get_models()


def get_extension_migration_paths() -> list[Path]:
    """Convenience: return all extension Alembic migration dirs."""
    return get_loader().get_migration_paths()


__all__ = [
    "ExtensionLoader",
    "get_loader",
    "load_extensions",
    "apply_server_hooks",
    "get_extension_models",
    "get_extension_migration_paths",
]
