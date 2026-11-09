"""Helpers for the Muse cloud art runtime client."""

from __future__ import annotations

import base64
import binascii
import math
import os
from dataclasses import dataclass, field
from typing import Any, Mapping, Optional, Protocol

from urllib.parse import urlparse

from airunner_services.runtimes.contracts import ArtInvocationRequest
from airunner_services.runtimes.muse_art_settings import (
    DEFAULT_BASE_URL, DEFAULT_MAX_IMAGE_BYTES, DEFAULT_MODEL,
    DEFAULT_TIMEOUT_S, MuseArtSettings,
)
from airunner_services.runtimes.muse_url_safety import guard_image_url

class MuseArtError(Exception):
    """Muse failure carrying a stable code and retryable flag."""

    def __init__(self, code: str, message: str, retryable: bool) -> None:
        super().__init__(message)
        self.code = code
        self.retryable = retryable

class MuseSession(Protocol):
    """HTTP session contract used by the Muse client."""

    def post(self, url: str, **kwargs: Any) -> Any: ...

    def get(self, url: str, **kwargs: Any) -> Any: ...

def validate_muse_invocation(invocation: ArtInvocationRequest) -> None:
    """Reject inputs the Muse image endpoint cannot honour."""
    if invocation.negative_prompt:
        raise ValueError("Muse does not support negative_prompt")
    if (invocation.metadata or {}).get("image_b64"):
        raise ValueError("Muse does not support image_b64 input")
    model = invocation.model or ""
    if len(model) > 128:
        raise ValueError("Muse model id is too long")
    if "/" in model or "\\" in model or model.endswith(".safetensors"):
        raise ValueError("Muse model must be a Muse model id, not a path")

def build_muse_payload(invocation: ArtInvocationRequest,
        model: str) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "model": model,
        "prompt": invocation.prompt,
        "n": invocation.num_images,
        "size": f"{invocation.width}x{invocation.height}",
    }
    if invocation.seed is not None:
        payload["seed"] = invocation.seed
    return payload

def status_error(status_code: int) -> MuseArtError:
    if status_code in (401, 403):
        return MuseArtError("muse_auth_error", "Muse auth failed", False)
    if status_code == 429:
        return MuseArtError("muse_rate_limited", "Muse rate limit", True)
    if 500 <= status_code <= 599:
        return MuseArtError("muse_upstream_error", "Muse error", True)
    if 400 <= status_code <= 499:
        return MuseArtError("muse_request_error", "Muse rejected", False)
    return MuseArtError("muse_upstream_error", "Muse failed", True)

def transport_error(exc: Exception) -> MuseArtError:
    timed_out = "timeout" in type(exc).__name__.lower()
    if timed_out or isinstance(exc, TimeoutError):
        return MuseArtError("muse_timeout", "Muse timed out", True)
    return MuseArtError("muse_upstream_error", "Muse request failed", True)

def checked_b64_image(value: str, max_bytes: int) -> str:
    try:
        raw = base64.b64decode(value, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise MuseArtError(
            "muse_malformed_response", "Muse invalid image", False
        ) from exc
    if len(raw) > max_bytes:
        raise MuseArtError(
            "muse_image_too_large", "Muse image too large", False
        )
    return value

def fetch_url_image(session: MuseSession, url: str,
        settings: MuseArtSettings) -> str:
    """Fetch one https image URL and return it base64-encoded."""
    try:
        guard_image_url(url)
    except ValueError as exc:
        code = "muse_invalid_image_url"
        raise MuseArtError(code, "Muse invalid image URL", False) from exc
    try:
        response = session.get(
            url, timeout=settings.timeout_s, allow_redirects=False,
            stream=True,
        )
    except Exception as exc:
        raise transport_error(exc) from exc
    status = int(getattr(response, "status_code", 200) or 200)
    if not 200 <= status <= 299:
        raise status_error(status)
    return _encode_content(response, settings)

def _check_content_length(response: Any, max_bytes: int) -> None:
    headers = getattr(response, "headers", None) or {}
    try:
        length = int(headers.get("content-length") or 0)
    except (TypeError, ValueError):
        length = 0
    if length > max_bytes:
        raise MuseArtError(
            "muse_image_too_large", "Muse image too large", False
        )


def _encode_content(response: Any, settings: MuseArtSettings) -> str:
    _check_content_length(response, settings.max_image_bytes)
    content = _bounded_content(response, settings.max_image_bytes)
    return base64.b64encode(content).decode("ascii")


def _too_large() -> MuseArtError:
    return MuseArtError("muse_image_too_large", "Muse image too large", False)


def _bounded_content(response: Any, max_bytes: int) -> bytes:
    iter_content = getattr(response, "iter_content", None)
    if not callable(iter_content):
        content = getattr(response, "content", b"") or b""
        if isinstance(content, str):
            content = content.encode("utf-8")
        if len(content) > max_bytes:
            raise _too_large()
        return bytes(content)
    chunks: list[bytes] = []
    total = 0
    for chunk in iter_content(65536):
        if not chunk:
            continue
        total += len(chunk)
        if total > max_bytes:
            raise _too_large()
        chunks.append(bytes(chunk))
    return b"".join(chunks)

def extract_images(
    payload: Any, session: MuseSession, settings: MuseArtSettings,
    max_images: int = 8,
) -> list[str]:
    """Return validated base64 images from one Muse response."""
    if not isinstance(payload, dict):
        raise _malformed()
    data = payload.get("data", payload.get("images"))
    if data is None or data == []:
        raise MuseArtError(
            "muse_missing_data", "Muse missing image data", False
        )
    if not isinstance(data, list):
        raise _malformed()
    if len(data) > max(1, max_images):
        raise MuseArtError(
            "muse_too_many_images", "Muse returned too many images", False
        )
    return [_one(item, session, settings) for item in data]

def _malformed() -> MuseArtError:
    return MuseArtError("muse_malformed_response", "Muse malformed", False)

def _one(item: Any, session: MuseSession,
        st: MuseArtSettings) -> str:
    if isinstance(item, str):
        return checked_b64_image(item, st.max_image_bytes)
    if not isinstance(item, dict):
        raise _malformed()
    b64 = item.get("b64_json") or item.get("b64")
    b64 = b64 or item.get("image_b64") or item.get("base64")
    if isinstance(b64, str) and b64:
        return checked_b64_image(b64, st.max_image_bytes)
    url = item.get("url") or item.get("image_url")
    if isinstance(url, dict):
        url = url.get("url")
    if isinstance(url, str) and url:
        return fetch_url_image(session, url, st)
    raise MuseArtError(
        "muse_missing_data", "Muse missing image data", False
    )

def post_images(
    session: MuseSession,
    settings: MuseArtSettings,
    invocation: ArtInvocationRequest,
    model: str,
) -> list[str]:
    url = f"{settings.base_url}/images/generations"
    headers = {"Authorization": f"Bearer {settings.api_key}",
        "Content-Type": "application/json"}
    try:
        response = session.post(
            url, json=build_muse_payload(invocation, model),
            headers=headers, timeout=settings.timeout_s,
        )
    except MuseArtError:
        raise
    except Exception as exc:
        raise transport_error(exc) from exc
    payload = _json_payload(response, settings, invocation.num_images)
    return extract_images(payload, session, settings, invocation.num_images)

def _json_payload(response: Any, settings: Any = None,
        num_images: int = 1) -> Any:
    status = int(getattr(response, "status_code", 200) or 200)
    if not 200 <= status <= 299:
        raise status_error(status)
    if settings is not None:
        _check_content_length(response, settings.max_image_bytes
            * max(1, num_images) * 3 + 65536)
    try:
        return response.json()
    except Exception as exc:
        raise MuseArtError(
            "muse_malformed_response", "Muse malformed JSON", False
        ) from exc

__all__ = ["DEFAULT_BASE_URL", "DEFAULT_MAX_IMAGE_BYTES", "DEFAULT_MODEL",
    "DEFAULT_TIMEOUT_S", "MuseArtError", "MuseArtSettings", "MuseSession",
    "build_muse_payload", "checked_b64_image", "extract_images",
    "fetch_url_image", "post_images", "status_error", "transport_error",
    "validate_muse_invocation"]
