"""Service-owned access policy helpers for external services."""

from __future__ import annotations

from typing import Mapping

from airunner_services.config.local_settings_store import get_bool_setting
from airunner_services.config.local_settings_store import set_setting
from airunner_services.config.local_settings_store import set_settings

PRIVACY_CONSENT_SHOWN_KEY = "privacy/consent_shown"
SERVICE_HUGGINGFACE_KEY = "privacy/allow_huggingface"
SERVICE_CIVITAI_KEY = "privacy/allow_civitai"
SERVICE_DUCKDUCKGO_KEY = "privacy/allow_duckduckgo"
SERVICE_OPENMETEO_KEY = "privacy/allow_openmeteo"
SERVICE_OPENROUTER_KEY = "privacy/allow_openrouter"
SERVICE_OPENAI_KEY = "privacy/allow_openai"

SERVICE_POLICY_KEYS = (
    SERVICE_HUGGINGFACE_KEY,
    SERVICE_CIVITAI_KEY,
    SERVICE_DUCKDUCKGO_KEY,
    SERVICE_OPENMETEO_KEY,
    SERVICE_OPENROUTER_KEY,
    SERVICE_OPENAI_KEY,
)

_SERVICE_DEFAULTS = {
    SERVICE_CIVITAI_KEY: True,
    SERVICE_DUCKDUCKGO_KEY: True,
    SERVICE_HUGGINGFACE_KEY: True,
    SERVICE_OPENAI_KEY: True,
    SERVICE_OPENMETEO_KEY: False,
    SERVICE_OPENROUTER_KEY: True,
}


def service_default(key: str) -> bool:
    """Return the default consent value for one external service."""
    return _SERVICE_DEFAULTS.get(key, True)


def privacy_consent_shown() -> bool:
    """Return whether the privacy consent screen has been acknowledged."""
    return get_bool_setting(PRIVACY_CONSENT_SHOWN_KEY, False)


def is_service_allowed(key: str) -> bool:
    """Return whether one external service is allowed by policy."""
    return get_bool_setting(key, service_default(key))


def set_privacy_consent_shown(shown: bool = True) -> None:
    """Persist whether the privacy consent dialog has been acknowledged."""
    set_setting(PRIVACY_CONSENT_SHOWN_KEY, shown)


def set_service_allowed(key: str, allowed: bool) -> None:
    """Persist one external service policy setting."""
    set_setting(key, allowed)


def set_service_settings(
    values: Mapping[str, bool],
    *,
    consent_shown: bool | None = None,
) -> None:
    """Persist multiple service policy settings in one write."""
    payload = {key: bool(value) for key, value in values.items()}
    if consent_shown is not None:
        payload[PRIVACY_CONSENT_SHOWN_KEY] = consent_shown
    set_settings(payload)


def is_huggingface_allowed() -> bool:
    """Return whether HuggingFace downloads are allowed."""
    return is_service_allowed(SERVICE_HUGGINGFACE_KEY)


def is_civitai_allowed() -> bool:
    """Return whether CivitAI downloads are allowed."""
    return is_service_allowed(SERVICE_CIVITAI_KEY)


def is_duckduckgo_allowed() -> bool:
    """Return whether DuckDuckGo search is allowed."""
    return is_service_allowed(SERVICE_DUCKDUCKGO_KEY)


def is_openmeteo_allowed() -> bool:
    """Return whether Open-Meteo weather access is allowed."""
    return is_service_allowed(SERVICE_OPENMETEO_KEY)


def is_openrouter_allowed() -> bool:
    """Return whether OpenRouter access is allowed."""
    return is_service_allowed(SERVICE_OPENROUTER_KEY)


def is_openai_allowed() -> bool:
    """Return whether OpenAI access is allowed."""
    return is_service_allowed(SERVICE_OPENAI_KEY)


__all__ = [
    "PRIVACY_CONSENT_SHOWN_KEY",
    "SERVICE_CIVITAI_KEY",
    "SERVICE_DUCKDUCKGO_KEY",
    "SERVICE_HUGGINGFACE_KEY",
    "SERVICE_OPENAI_KEY",
    "SERVICE_OPENMETEO_KEY",
    "SERVICE_OPENROUTER_KEY",
    "SERVICE_POLICY_KEYS",
    "is_civitai_allowed",
    "is_duckduckgo_allowed",
    "is_huggingface_allowed",
    "is_openai_allowed",
    "is_openmeteo_allowed",
    "is_openrouter_allowed",
    "is_service_allowed",
    "privacy_consent_shown",
    "service_default",
    "set_privacy_consent_shown",
    "set_service_allowed",
    "set_service_settings",
]
