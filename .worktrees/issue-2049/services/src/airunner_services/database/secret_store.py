"""Optional OS keyring integration for API credentials (GitHub issue #2035).

Hugging Face / CivitAI / LLM-provider API keys are stored in the OS keyring
when the optional ``keyring`` package is available. The database keeps only a
reference and the secret is injected back into serialized records at read
time.

Backward compatibility: in headless/unattended environments where no keyring
backend is available, the existing plaintext database columns remain as a
documented fallback and a warning is logged. ``keyring`` is intentionally an
optional dependency; nothing here raises when it is missing.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

_KEYRING_AVAILABLE = False
try:
    import keyring as _keyring  # type: ignore[import-not-found]

    _KEYRING_AVAILABLE = True
except Exception:  # pragma: no cover - optional dependency guard
    _keyring = None  # type: ignore[assignment]

_KEYRING_SERVICE = "airunner"

#: Canonical keyring key names for each stored credential.
SECRET_KEYS = {
    "hf_api_key_read_key": "application_settings/hf_api_key_read_key",
    "hf_api_key_write_key": "application_settings/hf_api_key_write_key",
    "civit_ai_api_key": "application_settings/civit_ai_api_key",
    "api_key": "llm_generator_settings/api_key",
}

#: Which credential columns belong to which model class.
MODEL_SECRET_COLUMNS = {
    "ApplicationSettings": {
        "hf_api_key_read_key",
        "hf_api_key_write_key",
        "civit_ai_api_key",
    },
    "LLMGeneratorSettings": {"api_key"},
}


def keyring_available() -> bool:
    """Return whether the optional OS keyring backend is usable."""
    return _KEYRING_AVAILABLE


def store_secret(column_key: str, value: str) -> str:
    """Persist one secret and return the value to store in the database.

    Returns an empty string when the secret was moved to the keyring (the DB
    column is cleared), or the plaintext value when the keyring is
    unavailable (documented headless fallback).
    """
    value = value or ""
    if not value:
        return ""
    key_name = SECRET_KEYS.get(column_key, column_key)
    if not _KEYRING_AVAILABLE:
        logger.warning(
            "keyring is not available; storing %s as plaintext in the "
            "local database (headless/unattended fallback). Install the "
            "'keyring' package for secure credential storage.",
            column_key,
        )
        return value
    try:
        _keyring.set_password(_KEYRING_SERVICE, key_name, value)
    except Exception as exc:
        logger.warning(
            "keyring backend failed for %s (%s); falling back to the "
            "plaintext database column.",
            column_key,
            exc,
        )
        return value
    return ""


def retrieve_secret(column_key: str, db_value: str) -> str:
    """Return one credential, preferring the OS keyring over the DB value."""
    db_value = db_value or ""
    key_name = SECRET_KEYS.get(column_key, column_key)
    if _KEYRING_AVAILABLE:
        try:
            stored = _keyring.get_password(_KEYRING_SERVICE, key_name)
            if stored:
                return stored
        except Exception as exc:
            logger.warning(
                "keyring read failed for %s (%s); using the database "
                "fallback value.",
                column_key,
                exc,
            )
    if db_value:
        logger.warning(
            "Credential for %s was read from the plaintext database "
            "fallback; install 'keyring' to store credentials securely.",
            column_key,
        )
    return db_value


def clear_secret(column_key: str, db_value: str) -> str:
    """Best-effort delete a keyring entry and return the DB value to store."""
    db_value = db_value or ""
    if not db_value and _KEYRING_AVAILABLE:
        key_name = SECRET_KEYS.get(column_key, column_key)
        try:
            _keyring.delete_password(_KEYRING_SERVICE, key_name)
        except Exception:
            # Nothing stored under this key; nothing to clear.
            pass
    return db_value


__all__ = [
    "MODEL_SECRET_COLUMNS",
    "SECRET_KEYS",
    "clear_secret",
    "keyring_available",
    "retrieve_secret",
    "store_secret",
]
