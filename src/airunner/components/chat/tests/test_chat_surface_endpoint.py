"""Tests for the chat surface's loopback endpoint resolution (#2230).

The resolver is the only place that answers "which origin hosts the
surface, and with which credential" — so it is tested without Qt.
"""

from __future__ import annotations

import pytest

from airunner.components.chat.gui.chat_surface_endpoint import (
    DAEMON_URL_ENV,
    ChatSurfaceEndpoint,
    daemon_base_url,
    resolve_chat_surface_endpoint,
)
from airunner_services.api import loopback_token


@pytest.fixture()
def isolated_token(tmp_path, monkeypatch):
    """Point the token store at a temp path and reset its cache."""
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


def test_index_url_normalizes_a_trailing_slash() -> None:
    """The entry URL never doubles the separator."""
    endpoint = ChatSurfaceEndpoint(
        base_url="http://127.0.0.1:8188/", token="token"
    )
    assert endpoint.index_url == "http://127.0.0.1:8188/index.html"


def test_daemon_url_override_wins(monkeypatch) -> None:
    """An explicit origin overrides the persisted daemon configuration."""
    monkeypatch.setenv(DAEMON_URL_ENV, "http://127.0.0.1:9999/")
    assert daemon_base_url() == "http://127.0.0.1:9999"


def test_endpoint_pairs_the_daemon_origin_with_the_loopback_token(
    monkeypatch, isolated_token
) -> None:
    """The resolved endpoint is the daemon origin plus its token."""
    monkeypatch.delenv(DAEMON_URL_ENV, raising=False)
    endpoint = resolve_chat_surface_endpoint()
    assert endpoint.base_url.startswith("http://")
    assert endpoint.token
    assert endpoint.token == loopback_token.get_or_create_loopback_token()
    assert endpoint.index_url == f"{endpoint.base_url}/index.html"
