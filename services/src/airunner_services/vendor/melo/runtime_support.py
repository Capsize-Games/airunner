"""Thread-safe runtime helpers for Melo vendor integrations.

This module previously imported AIRUNNER_BASE_PATH and read the
application's PathSettings database model directly, and logged
through the application's shared logger factory. A vendored
third-party library should not depend on this project at all (issue
#2190). The three lookups this module needs (an explicit TTS model
root override, a base data directory for the default TTS model path,
and a base data directory for the g2p cache) are now injected by the
host as resolver callbacks, mirroring the
set_log_base_path_resolver pattern already used by
airunner_common.get_logger. See
airunner_services.runtimes.openvoice_model_manager for the
registration that replicates the previous PathSettings-based
behaviour exactly.
"""

import logging
import os
from pathlib import Path
from typing import Callable, Optional

_LOGGER_NAME = "airunner_services.vendor.melo"

_tts_model_root_resolver: Optional[Callable[[], Optional[str]]] = None
_tts_model_base_resolver: Optional[Callable[[], str]] = None
_cache_base_resolver: Optional[Callable[[], str]] = None


def set_tts_model_root_resolver(
    fn: Callable[[], Optional[str]],
) -> None:
    """Register a resolver for an explicit TTS model root override.

    ``fn`` should return an absolute path, or None/"" if no override
    is configured (see resolve_tts_model_root).
    """
    global _tts_model_root_resolver
    _tts_model_root_resolver = fn


def set_tts_model_base_resolver(fn: Callable[[], str]) -> None:
    """Register a resolver for the default TTS model base directory.

    Used only when no explicit root override is configured; the
    default TTS model root is ``<base>/text/models/tts``.
    """
    global _tts_model_base_resolver
    _tts_model_base_resolver = fn


def set_cache_base_resolver(fn: Callable[[], str]) -> None:
    """Register a resolver for the g2p cache's base directory.

    The cache path is ``<base>/cache/melo``.
    """
    global _cache_base_resolver
    _cache_base_resolver = fn


def get_melo_logger():
    """Return a standard-library logger for the Melo vendor tree.

    Configuration (handlers, level, file output) is the host's job.
    """
    return logging.getLogger(_LOGGER_NAME)


def normalize_tts_model_root(path: str) -> str:
    """Return the shared TTS root for one configured model path."""
    expanded = os.path.expanduser(path)
    candidate = Path(expanded)
    if candidate.name == "openvoice" or (
        candidate / "checkpoints_v2"
    ).exists():
        return str(candidate.parent)
    return expanded


def _default_tts_model_root() -> str:
    """Fallback root used when no resolver is registered at all."""
    return os.path.join(
        os.path.expanduser("~"), ".cache", "airunner-melo-tts"
    )


def resolve_tts_model_root() -> str:
    """Return the configured TTS model root without bootstrapping the app."""
    env_override = os.environ.get("AIRUNNER_TTS_MODEL_PATH", "").strip()
    if env_override:
        return normalize_tts_model_root(env_override)

    if _tts_model_root_resolver is not None:
        override = _tts_model_root_resolver()
        if override:
            return normalize_tts_model_root(override)

    if _tts_model_base_resolver is not None:
        base = _tts_model_base_resolver()
        if base:
            return os.path.join(
                os.path.expanduser(base), "text/models/tts"
            )

    return _default_tts_model_root()


def resolve_tts_model_path(model_id: str) -> str:
    """Resolve one Melo model id to its local filesystem path."""
    return os.path.join(resolve_tts_model_root(), model_id)


def resolve_cache_root() -> str:
    """Return the directory Melo caches g2p artifacts under."""
    if _cache_base_resolver is not None:
        base = _cache_base_resolver()
        if base:
            return os.path.join(os.path.expanduser(base), "cache", "melo")
    return os.path.join(_default_tts_model_root(), "cache")
