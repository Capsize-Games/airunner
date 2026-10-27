"""Pluggable application settings — Django-style LazySettings.

Resolution order:
    1. ``default_settings.py`` (checked-in defaults)
    2. ``.env`` file (load_dotenv, already called by settings.py)
    3. Environment variables at runtime (``AIRUNNER_*``)
    4. Preset overlays (development / production)

Usage::

    from airunner_services.conf import settings
    db_url = settings.DATABASE_URL
"""

from __future__ import annotations

import os
from typing import Any

from dotenv import load_dotenv

# Load .env file before any settings resolution.
# This runs on every import of this module, which is the first settings
# module imported in most import chains.  The check is cheap — dotenv
# caches after the first call.
load_dotenv()


def _env_bool(name: str, default: str = "0") -> bool:
    """Return one boolean environment flag."""
    return os.environ.get(name, default) == "1"


def _apply_preset(store: dict[str, Any]) -> None:
    """Overlay the selected preset on top of the store."""
    mode = store.get("DEPLOYMENT_MODE", "development")
    module_name = "production" if mode == "production" else "development"
    full_name = f"airunner_services.conf.presets.{module_name}"
    import importlib  # noqa: PLC0415

    preset = importlib.import_module(full_name)
    for attr in dir(preset):
        if attr.isupper():
            store[attr] = getattr(preset, attr)


def _coerce_value(key: str, value: str) -> Any:
    """Coerce env-var strings to their likely Python type."""
    lowered = value.lower().strip()
    if lowered in ("true", "1", "yes", "on"):
        return True
    if lowered in ("false", "0", "no", "off"):
        return False
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        pass
    return value


class LazySettings:
    """Settings container resolved lazily on first attribute access."""

    def __init__(self) -> None:
        self._store: dict[str, Any] = {}
        self._resolved = False

    def _resolve(self) -> None:
        if self._resolved:
            return

        # 1. Defaults
        from airunner_services.conf import default_settings  # noqa: PLC0415

        for attr in dir(default_settings):
            if attr.isupper():
                self._store[attr] = getattr(default_settings, attr)

        # 2. Environment variable overrides (.env + runtime)
        # Strip the AIRUNNER_ prefix so AIRUNNER_EXTENSIONS sets the
        # EXTENSIONS key, AIRUNNER_DATABASE_BACKEND sets DATABASE_BACKEND,
        # etc.  Settings whose natural name already includes the prefix
        # (e.g. AIRUNNER_BASE_PATH) are stored under both forms.
        for key, value in os.environ.items():
            if key.startswith("AIRUNNER_"):
                self._store[key] = _coerce_value(key, value)
                stripped = key[len("AIRUNNER_") :]
                # Only set the stripped key if it doesn't already exist
                # from the defaults (handles the case where the default
                # uses the prefixed name like AIRUNNER_BASE_PATH).
                self._store[stripped] = _coerce_value(key, value)

        # 3. Preset overlay
        _apply_preset(self._store)

        # 4. Extension defaults — applied lazily after extensions load

        # 4. Normalise string-typed extension list
        raw = self._store.get("EXTENSIONS")
        if isinstance(raw, str):
            self._store["EXTENSIONS"] = [
                s.strip() for s in raw.split(",") if s.strip()
            ]

        # 5. Computed values
        self._store["DATABASE_URL"] = self._build_db_url()
        self._store["AIRUNNER_DB_URL"] = self._store["DATABASE_URL"]

        self._resolved = True

    # ------------------------------------------------------------------
    # Computed helpers
    # ------------------------------------------------------------------
    def _build_db_url(self) -> str:
        # An explicit URL (AIRUNNER_DATABASE_URL / DATABASE_URL) always wins
        # so operators can point at an existing database without juggling
        # the POSTGRES_* parts.
        explicit = str(self._store.get("DATABASE_URL", "") or "").strip()
        if explicit:
            return explicit
        backend = self._store.get("DATABASE_BACKEND", "sqlite")
        if backend == "postgresql":
            user = self._store.get("POSTGRES_USER", "airunner")
            password = self._store.get("POSTGRES_PASSWORD", "")
            host = self._store.get("POSTGRES_HOST", "localhost")
            port = self._store.get("POSTGRES_PORT", 5432)
            db = self._store.get("POSTGRES_DB", "airunner")
            return f"postgresql://{user}:{password}" f"@{host}:{port}/{db}"
        # SQLite
        base = self._store.get("AIRUNNER_BASE_PATH", "~/.local/share/airunner")
        base = os.path.expanduser(base)
        db_name = self._store.get("SQLITE_DB_NAME", "airunner.db")
        db_dir = os.path.join(base, "data")
        os.makedirs(db_dir, exist_ok=True)
        return f"sqlite:///{os.path.join(db_dir, db_name)}"

    # ------------------------------------------------------------------
    # Attributes
    # ------------------------------------------------------------------
    def __getattr__(self, name: str) -> Any:
        if not name.startswith("_") and name.isupper():
            self._resolve()
            try:
                return self._store[name]
            except KeyError:
                raise AttributeError(
                    f"Settings has no attribute '{name}'"
                ) from None
        msg = f"'{type(self).__name__}' has no attribute '{name}'"
        raise AttributeError(msg)

    def __contains__(self, name: str) -> bool:
        self._resolve()
        return name in self._store

    def get(self, name: str, default: Any = None) -> Any:
        """Return one setting or a default when not found."""
        self._resolve()
        return self._store.get(name, default)


settings = LazySettings()

__all__ = ["settings", "LazySettings"]
