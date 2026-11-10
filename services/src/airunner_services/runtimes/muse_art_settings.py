"""Settings for the Muse cloud art runtime client."""

from __future__ import annotations

import math
import os
from dataclasses import dataclass, field
from typing import Mapping, Optional
from urllib.parse import urlparse

DEFAULT_BASE_URL = "https://api.meta.ai/v1"
DEFAULT_MODEL = "muse-image-1.0"
DEFAULT_TIMEOUT_S = 120.0
DEFAULT_MAX_IMAGE_BYTES = 25 * 1024 * 1024


@dataclass(frozen=True)
class MuseArtSettings:
    """Resolved Muse settings; the key stays out of repr/logs."""

    api_key: str = field(default="", repr=False)
    base_url: str = DEFAULT_BASE_URL
    model: str = DEFAULT_MODEL
    timeout_s: float = DEFAULT_TIMEOUT_S
    max_image_bytes: int = DEFAULT_MAX_IMAGE_BYTES

    @classmethod
    def from_env(
        cls, environ: Optional[Mapping[str, str]] = None
    ) -> "MuseArtSettings":
        """Build settings from MODEL_API_KEY and AIRUNNER_MUSE_*."""
        env = os.environ if environ is None else environ
        return cls(
            api_key=env.get("MODEL_API_KEY", ""),
            base_url=_base_url(env.get("AIRUNNER_MUSE_BASE_URL")),
            model=_model(env.get("AIRUNNER_MUSE_MODEL")),
            timeout_s=_timeout(env.get("AIRUNNER_MUSE_TIMEOUT_S")),
            max_image_bytes=_max_bytes(
                env.get("AIRUNNER_MUSE_MAX_IMAGE_BYTES")
            ),
        )

def _base_url(raw: Optional[str]) -> str:
    cleaned = (raw or DEFAULT_BASE_URL).strip().rstrip("/")
    if not cleaned:
        raise ValueError("AIRUNNER_MUSE_BASE_URL must not be blank")
    parsed = urlparse(cleaned)
    host = (parsed.hostname or "").lower()
    loopback = host in ("localhost", "127.0.0.1", "::1")
    if parsed.scheme != "https" and not (parsed.scheme == "http" and loopback):
        raise ValueError("AIRUNNER_MUSE_BASE_URL must use https")
    return cleaned

def _model(raw: Optional[str]) -> str:
    return (raw or "").strip() or DEFAULT_MODEL

def _timeout(raw: Optional[str]) -> float:
    if raw is None or not raw.strip():
        return DEFAULT_TIMEOUT_S
    try:
        value = float(raw)
    except ValueError as exc:
        raise ValueError("AIRUNNER_MUSE_TIMEOUT_S must be a number") from exc
    if not math.isfinite(value) or value <= 0 or value > 600:
        raise ValueError("AIRUNNER_MUSE_TIMEOUT_S out of range")
    return value

def _max_bytes(raw: Optional[str]) -> int:
    if raw is None or not raw.strip():
        return DEFAULT_MAX_IMAGE_BYTES
    try:
        value = int(raw)
    except ValueError as exc:
        msg = "AIRUNNER_MUSE_MAX_IMAGE_BYTES must be an integer"
        raise ValueError(msg) from exc
    if value <= 0:
        raise ValueError(
            "AIRUNNER_MUSE_MAX_IMAGE_BYTES must be positive"
        )
    return value

__all__ = ["DEFAULT_BASE_URL", "DEFAULT_MAX_IMAGE_BYTES", "DEFAULT_MODEL",
    "DEFAULT_TIMEOUT_S", "MuseArtSettings"]
