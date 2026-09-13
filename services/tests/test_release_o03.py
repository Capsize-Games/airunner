"""Regression tests for release issue O03.

Proves the diagnostics/crash-capture path is private and user-controlled:

- Crash-log writes are sanitized the same way regular application logs
  are (URLs, filesystem paths, recognizable tokens) — crash_handler.py
  wrote directly to disk, bypassing the logging module's
  ``LogHygieneFilter`` entirely, until this change.
- The new sanitized diagnostics export contains only IDs/versions/
  platform identity/failure codes, never prompts, file contents,
  transcripts, tokens, raw tool results, or full tracebacks — and makes
  no network attempt.
- Credential-bearing files on disk (the loopback token, the SQLite
  database) keep owner-only (0600) permissions.

Uses only a temporary data directory; never inspects or requires real
credentials, and no GUI/model/network access.
"""

from __future__ import annotations

import json
import os
import stat
from unittest import mock

import pytest

import airunner.crash_handler as crash_handler
from airunner_common.logging_utils import sanitize_log_text
from airunner_services.api import loopback_token
from airunner_services.database.setup_database import (
    _restrict_sqlite_file_permissions,
)

_SENSITIVE_PATH = "/home/user/secret_project/notes.txt"
_SENSITIVE_TOKEN = "sk-1234567890abcdefghijklmnop"
_SENSITIVE_URL = "https://example.com/internal/report?id=42"


@pytest.fixture()
def crash_log_dir(tmp_path):
    crash_handler.install_crash_handlers(log_dir=str(tmp_path))
    return tmp_path


def _raise_sensitive_exception() -> tuple:
    try:
        raise ValueError(
            f"failed to load {_SENSITIVE_PATH} with api_key={_SENSITIVE_TOKEN} "
            f"from {_SENSITIVE_URL}"
        )
    except ValueError:
        import sys

        return sys.exc_info()


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


# --- Crash log write-path sanitization ---


def test_gui_log_never_contains_raw_path_token_or_url(crash_log_dir) -> None:
    exc_info = _raise_sensitive_exception()
    crash_handler.report_uncaught_exception(*exc_info)

    gui_log = (crash_log_dir / "gui.log").read_text(encoding="utf-8")
    assert _SENSITIVE_PATH not in gui_log
    assert _SENSITIVE_TOKEN not in gui_log
    assert _SENSITIVE_URL not in gui_log
    assert "ValueError" in gui_log  # the failure type itself is still useful


# --- Diagnostics export ---


def test_build_diagnostics_export_excludes_raw_content(crash_log_dir) -> None:
    exc_info = _raise_sensitive_exception()
    crash_handler.report_uncaught_exception(*exc_info)

    payload = crash_handler.build_diagnostics_export()
    serialized = json.dumps(payload)

    assert _SENSITIVE_PATH not in serialized
    assert _SENSITIVE_TOKEN not in serialized
    assert _SENSITIVE_URL not in serialized
    assert payload["recent_failures"][-1]["type"] == "ValueError"
    assert {"application_version", "python_version", "platform"} <= payload.keys()


def test_extract_failure_codes_ignores_traceback_body_lines() -> None:
    """Only the unindented "SomeError: message" line is a failure code —
    indented stack-frame/source lines (which could contain a prompt, a
    file's content, or a local variable repr) are never captured."""
    log_text = (
        "Traceback (most recent call last):\n"
        '  File "/home/user/app.py", line 42, in run\n'
        "    do_something(prompt='secret prompt text', path='/home/user/x')\n"
        "ValueError: something went wrong\n"
    )
    failures = crash_handler._extract_failure_codes(log_text)
    assert failures == [{"type": "ValueError", "message": "something went wrong"}]
    combined = json.dumps(failures)
    assert "secret prompt text" not in combined
    assert "/home/user" not in combined


def test_extract_failure_codes_truncates_long_messages() -> None:
    log_text = f"RuntimeError: {'x' * 500}\n"
    failures = crash_handler._extract_failure_codes(log_text)
    assert len(failures[0]["message"]) <= 203  # 200 chars + "..."


def test_export_diagnostics_writes_local_json_file(crash_log_dir, tmp_path) -> None:
    destination = tmp_path / "export" / "diagnostics.json"
    result_path = crash_handler.export_diagnostics(str(destination))

    assert result_path == str(destination)
    assert destination.exists()
    payload = json.loads(destination.read_text(encoding="utf-8"))
    assert "application_version" in payload


def test_export_diagnostics_makes_no_network_attempt(crash_log_dir, tmp_path) -> None:
    with mock.patch("socket.socket") as sock:
        crash_handler.export_diagnostics(str(tmp_path / "diagnostics.json"))
        sock.assert_not_called()


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
