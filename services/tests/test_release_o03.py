"""Regression tests for release issue O03 (services-only remainder).

Proves the log-sanitization path and credential file permissions:

- ``sanitize_log_text`` redacts URLs, filesystem paths and
  recognizable tokens while leaving ordinary text unchanged.
- Credential-bearing files on disk (the loopback token, the SQLite
  database) keep owner-only (0600) permissions.

The former crash_handler/diagnostics-export tests were removed with
the desktop client (``src/airunner/crash_handler.py``); the daemon
logs through the shared ``LogHygieneFilter`` instead.

Uses only a temporary data directory; never inspects or requires real
credentials, and no GUI/model/network access.
"""

from __future__ import annotations

import stat

import pytest

from airunner_common.logging_utils import sanitize_log_text
from airunner_services.api import loopback_token
from airunner_services.database.setup_database import (
    _restrict_sqlite_file_permissions,
)

_SENSITIVE_PATH = "/home/user/secret_project/notes.txt"
# Must look like a real secret: sanitize_log_text only redacts
# token-shaped values, and correctly leaves the already-redacted
# placeholder "[REDACTED]" alone.
_SENSITIVE_TOKEN = "sk-live-abc123XYZ789"
_SENSITIVE_URL = "https://example.com/internal/report?id=42"


# --- Direct sanitizer unit tests ---


def test_sanitize_log_text_redacts_known_token_prefixes() -> None:
    result = sanitize_log_text(f"Authorization: Bearer {_SENSITIVE_TOKEN}")
    assert _SENSITIVE_TOKEN not in result
    assert "token_hash=" in result


def test_sanitize_log_text_redacts_generic_key_value_tokens() -> None:
    result = sanitize_log_text("api_key=abcdefghijklmnopqrstuvwx")
    assert "abcdefghijklmnopqrstuvwx" not in result
    assert "token_hash=" in result


def test_sanitize_log_text_redacts_paths_and_urls() -> None:
    result = sanitize_log_text(f"reading {_SENSITIVE_PATH} from {_SENSITIVE_URL}")
    assert _SENSITIVE_PATH not in result
    assert _SENSITIVE_URL not in result


def test_sanitize_log_text_leaves_ordinary_text_unchanged() -> None:
    assert sanitize_log_text("model loaded successfully") == (
        "model loaded successfully"
    )


# --- Credential file permissions ---


@pytest.fixture()
def isolated_loopback_token(tmp_path, monkeypatch):
    monkeypatch.setattr(
        loopback_token,
        "loopback_token_path",
        lambda: tmp_path / "config" / "loopback_token",
    )
    loopback_token._cache_loaded = False
    loopback_token._cached_token = None
    yield tmp_path / "config" / "loopback_token"
    loopback_token._cache_loaded = False
    loopback_token._cached_token = None


def test_loopback_token_file_is_owner_only(isolated_loopback_token) -> None:
    loopback_token.get_or_create_loopback_token()
    mode = stat.S_IMODE(isolated_loopback_token.stat().st_mode)
    assert mode == 0o600, f"loopback token file mode was {oct(mode)}"


def test_sqlite_database_file_is_owner_only(tmp_path) -> None:
    db_path = tmp_path / "airunner.sqlite"
    db_path.write_text("")  # simulate an already-created database file
    _restrict_sqlite_file_permissions(f"sqlite:///{db_path}")
    mode = stat.S_IMODE(db_path.stat().st_mode)
    assert mode == 0o600, f"database file mode was {oct(mode)}"
