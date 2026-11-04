"""Regression tests: pre-existing loopback token file must be hardened on load.

A token file left behind with mode 0644 (or a symlink planted at the token
path) must be tightened to 0600 — or refused — rather than silently trusted.
"""

from __future__ import annotations

import os
import stat

import pytest

from airunner_services.api import loopback_token


@pytest.fixture()
def isolated_token(tmp_path, monkeypatch):
    """Point the token store at a temp path and reset its module cache."""
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


def _mode(path) -> int:
    return stat.S_IMODE(os.stat(path).st_mode)


def test_fresh_token_created_private(isolated_token) -> None:
    """Baseline: a newly created token file is 0600."""
    token = loopback_token.get_or_create_loopback_token()
    assert token
    assert _mode(isolated_token) == 0o600


def test_preexisting_world_readable_file_is_tightened(isolated_token) -> None:
    """A 0644 token left by an older release must be chmodded to 0600."""
    isolated_token.parent.mkdir(parents=True, exist_ok=True)
    isolated_token.write_text("previous-token-value\n", encoding="utf-8")
    os.chmod(isolated_token, 0o644)

    token = loopback_token.get_or_create_loopback_token()

    assert token == "previous-token-value"
    assert _mode(isolated_token) == 0o600


def test_preexisting_group_readable_file_is_tightened(isolated_token) -> None:
    """A 0640 token file must be tightened to 0600 as well."""
    isolated_token.parent.mkdir(parents=True, exist_ok=True)
    isolated_token.write_text("previous-token-value\n", encoding="utf-8")
    os.chmod(isolated_token, 0o640)

    token = loopback_token.get_or_create_loopback_token()

    assert token == "previous-token-value"
    assert _mode(isolated_token) == 0o600


def test_symlink_at_token_path_is_refused_or_replaced(
    isolated_token, tmp_path
) -> None:
    """A symlink at the token path must not be followed for token reads."""
    target = tmp_path / "attacker-controlled"
    target.write_text("planted-token\n", encoding="utf-8")
    isolated_token.parent.mkdir(parents=True, exist_ok=True)
    isolated_token.symlink_to(target)

    token = loopback_token.get_or_create_loopback_token()

    assert token != "planted-token", "symlink target must never become the token"
    assert not isolated_token.is_symlink(), "symlink must be replaced"
    assert _mode(isolated_token) == 0o600
