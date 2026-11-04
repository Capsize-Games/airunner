"""Regression tests: WebSocket cross-origin and tenant-key scoping.

Sockets must enforce the same Origin allowlist as HTTP, require the same
credentials, and scope tenant context from headers exactly like the HTTP
tenant middleware does.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from airunner_services.api.routes.ws_auth import websocket_auth_failed
from airunner_services.api.server import is_allowed_origin
from airunner_services.data.tenant import get_tenant_key


def _ws_state(**overrides):
    defaults = {
        "api_key": "",
        "require_api_key": False,
        "insecure_no_auth": False,
        "allowed_origins": ["http://localhost", "http://localhost:*"],
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


class _FakeWS:
    """Minimal WebSocket double for the shared auth policy."""

    def __init__(
        self,
        *,
        headers: dict | None = None,
        client_host: str = "127.0.0.1",
        state=None,
    ) -> None:
        self.headers = dict(headers or {})
        self.client = SimpleNamespace(host=client_host)
        self.query_params: dict = {}
        self.app = SimpleNamespace(state=state or _ws_state())


# --- Origin allowlist -------------------------------------------------------


@pytest.mark.parametrize(
    "origin",
    ["http://localhost", "http://localhost:8188"],
)
def test_exact_and_wildcard_port_origins_allowed(origin: str) -> None:
    assert (
        is_allowed_origin(origin, ["http://localhost", "http://localhost:*"])
        is True
    )


@pytest.mark.parametrize(
    "origin",
    [
        "http://localhost.evil.example",
        "http://localhost.evil.example:8188",
        "http://evil-localhost",
        "http://127.0.0.1",
        "",
        "not-a-url",
        "http://localhost.evil.example:8188",
    ],
)
def test_lookalike_and_unlisted_origins_rejected(origin: str) -> None:
    assert (
        is_allowed_origin(origin, ["http://localhost", "http://localhost:*"])
        is False
    )


def test_cross_origin_socket_rejected_before_auth() -> None:
    """A disallowed Origin fails the socket even with no auth configured."""
    ws = _FakeWS(
        headers={"origin": "http://localhost.evil.example"},
        state=_ws_state(insecure_no_auth=True),
    )
    assert websocket_auth_failed(ws) is True


def test_unauthenticated_loopback_socket_rejected() -> None:
    """A loopback socket without the token is refused like HTTP is."""
    from airunner_services.api import loopback_token

    loopback_token._cache_loaded = False
    loopback_token._cached_token = None
    ws = _FakeWS(headers={"origin": "http://localhost"})
    try:
        assert websocket_auth_failed(ws) is True
    finally:
        loopback_token._cache_loaded = False
        loopback_token._cached_token = None


# --- Tenant scoping on sockets ----------------------------------------------


def test_socket_scopes_tenant_from_header(tmp_path, monkeypatch) -> None:
    """A socket carrying ``x-tenant-key`` must scope tenant context.

    Mirrors the HTTP tenant middleware: loopback sockets may select a
    tenant from headers, so per-tenant DB scoping applies on sockets too.
    """
    from airunner_services.api import loopback_token

    monkeypatch.setattr(
        loopback_token,
        "loopback_token_path",
        lambda: tmp_path / "config" / "loopback_token",
    )
    loopback_token._cache_loaded = False
    loopback_token._cached_token = None
    from airunner_services.data.tenant import reset_tenant_key, set_tenant_key

    baseline = set_tenant_key(None)
    try:
        token = loopback_token.get_or_create_loopback_token()
        ws = _FakeWS(
            headers={
                "origin": "http://localhost",
                "x-tenant-key": "tenant-acme",
                "x-airunner-token": token,
            }
        )
        assert websocket_auth_failed(ws) is False
        assert get_tenant_key() == "tenant-acme"
    finally:
        reset_tenant_key(baseline)
        loopback_token._cache_loaded = False
        loopback_token._cached_token = None


def test_socket_without_tenant_header_leaves_default_scope() -> None:
    """No tenant header means the default (None) scope stays active."""
    ws = _FakeWS(headers={"origin": "http://localhost"})
    websocket_auth_failed(ws)
    assert get_tenant_key() is None
