"""Optional OS keyring integration for API credentials (GitHub issue #2035).

Hugging Face / CivitAI / LLM-provider API keys are stored in the OS keyring
when the optional ``keyring`` package is available. The database keeps only a
reference and the secret is injected back into serialized records at read
time.

Plaintext database persistence is never silent: when no keyring backend
is available (or the backend fails), persisting a secret requires explicit
opt-in via the ``AIRUNNER_ALLOW_PLAINTEXT_SECRETS=1`` environment variable.
Without that opt-in, :func:`store_secret` raises instead of writing
plaintext to the database. ``keyring`` stays an optional dependency, and
reading back previously stored plaintext values keeps working (with a
warning) so keyring-less setups are not locked out of existing data.
"""

from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)

#: Explicit opt-in for plaintext database persistence when no keyring
#: backend is usable. Anything other than ``"1"`` means "not allowed".
PLAINTEXT_OPT_IN_ENV_VAR = "AIRUNNER_ALLOW_PLAINTEXT_SECRETS"


def plaintext_persistence_allowed() -> bool:
    """Return whether plaintext secret persistence was explicitly allowed."""
    return os.environ.get(PLAINTEXT_OPT_IN_ENV_VAR) == "1"


def _require_plaintext_opt_in(column_key: str) -> None:
    """Raise unless plaintext persistence was explicitly opted into."""
    if plaintext_persistence_allowed():
        return
    raise RuntimeError(
        f"Cannot persist credential for {column_key!r} without a "
        "usable OS keyring backend: refusing to write plaintext to the "
        "local database. Install the 'keyring' package, or explicitly "
        f"opt in to plaintext storage with {PLAINTEXT_OPT_IN_ENV_VAR}=1."
    )

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
    unavailable *and* plaintext persistence was explicitly opted into via
    ``AIRUNNER_ALLOW_PLAINTEXT_SECRETS=1``. Raises :class:`RuntimeError`
    instead of silently persisting plaintext otherwise.
    """
    value = value or ""
    if not value:
        return ""
    key_name = SECRET_KEYS.get(column_key, column_key)
    if not _KEYRING_AVAILABLE:
        _require_plaintext_opt_in(column_key)
        logger.warning(
            "keyring is not available; storing %s as plaintext in the "
            "local database (explicit "
            "AIRUNNER_ALLOW_PLAINTEXT_SECRETS=1 opt-in). Install the "
            "'keyring' package for secure credential storage.",
            column_key,
        )
        return value
    try:
        _keyring.set_password(_KEYRING_SERVICE, key_name, value)
    except Exception as exc:
        _require_plaintext_opt_in(column_key)
        logger.warning(
            "keyring backend failed for %s (%s); falling back to the "
            "plaintext database column (explicit "
            "AIRUNNER_ALLOW_PLAINTEXT_SECRETS=1 opt-in).",
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
    "PLAINTEXT_OPT_IN_ENV_VAR",
    "SECRET_KEYS",
    "clear_secret",
    "keyring_available",
    "plaintext_persistence_allowed",
    "retrieve_secret",
    "store_secret",
]
