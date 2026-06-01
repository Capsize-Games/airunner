"""Base-path helpers for art model discovery."""

import os
from pathlib import Path
from typing import Any, Optional

from airunner_services.database.models.generator_settings import (
    GeneratorSettings,
)
from airunner_services.database.models.path_settings import PathSettings
from airunner_services.database.session import session_scope
from airunner_services.settings import AIRUNNER_ART_MODEL_PATH

_DEFAULT_BASE_PATH = Path(
    os.path.expanduser(os.path.join("~", ".local", "share", "airunner"))
)


# Database-backed path settings


def query_first(model_class: type[Any]) -> Any:
    """Return the first database record for one model class."""
    try:
        with session_scope() as session:
            return session.query(model_class).first()
    except Exception:
        return None


def service_base_path() -> Path:
    """Return the configured AIRunner base path."""
    path_settings = query_first(PathSettings)
    base_path = ""
    if path_settings is not None:
        base_path = (getattr(path_settings, "base_path", "") or "").strip()
    if base_path:
        return Path(base_path).expanduser()
    return _DEFAULT_BASE_PATH


def art_model_base_dir() -> Path:
    """Return the base directory for local art models."""
    return service_base_path() / "art" / "models"


def generator_settings_record() -> Optional[GeneratorSettings]:
    """Return the first generator settings record when available."""
    return query_first(GeneratorSettings)


def existing_path(path_value: str) -> str:
    """Return one existing configured path or an empty string."""
    value = (path_value or "").strip()
    if not value:
        return ""
    return value if Path(value).expanduser().exists() else ""


def configured_art_model_path() -> str:
    """Return the configured art model path when it exists locally."""
    return existing_path(AIRUNNER_ART_MODEL_PATH or "")