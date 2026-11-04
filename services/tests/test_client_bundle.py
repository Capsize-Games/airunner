"""Tests for explicitly configured client bundle serving.

The bundle is disabled by default. When configured, it must be reachable over
loopback under the same loopback-token policy as the rest of the API.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi import FastAPI
from starlette.testclient import TestClient

from airunner_services.api import loopback_token
from airunner_services.api import server as server_module
from airunner_services.api.routes.client_bundle import (
    BUNDLE_ENV,
    bundle_directory,
    mount_client_bundle,
)
from airunner_services.api.server import create_app


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


@pytest.fixture()
def bundle(tmp_path) -> Path:
    """Write a minimal built-bundle layout to a temp directory."""
    directory = tmp_path / "dist"
    (directory / "assets").mkdir(parents=True)
    (directory / "index.html").write_text("<html></html>", encoding="utf-8")
    (directory / "assets" / "app.js").write_text("// built", encoding="utf-8")
    return directory


def _client(monkeypatch) -> tuple[TestClient, dict]:
    """Return a loopback-authenticated client plus its auth headers."""
    monkeypatch.setenv("AIRUNNER_API_KEY", "")
    monkeypatch.setenv("AIRUNNER_INSECURE_NO_AUTH", "0")
    monkeypatch.setattr(server_module, "is_loopback_request", lambda c: True)
    app = create_app()
    app.state.runtime_registry = None
    token = loopback_token.get_or_create_loopback_token()
    return TestClient(app), {"X-Airunner-Token": token}


def test_bundle_directory_requires_an_index(tmp_path, monkeypatch) -> None:
    """Only an explicit directory with an index document is accepted."""
    monkeypatch.delenv(BUNDLE_ENV, raising=False)
    assert bundle_directory() is None

    empty = tmp_path / "empty"
    empty.mkdir()
    monkeypatch.setenv(BUNDLE_ENV, str(empty))
    assert bundle_directory() is None


def test_bundle_directory_resolves_the_built_bundle(
    bundle: Path, monkeypatch
) -> None:
    """An explicit directory with an index file resolves to itself."""
    monkeypatch.setenv(BUNDLE_ENV, str(bundle))
    assert bundle_directory() == bundle


def test_bundle_is_not_mounted_when_unconfigured(monkeypatch) -> None:
    """No bundle is mounted or probed when the opt-in is unset."""
    monkeypatch.delenv(BUNDLE_ENV, raising=False)

    def unexpected_probe(self):
        raise AssertionError(f"unexpected bundle filesystem probe: {self}")

    monkeypatch.setattr(Path, "is_file", unexpected_probe)
    app = FastAPI()
    assert mount_client_bundle(app) is False
    assert not any(
        getattr(route, "name", None) == "client-bundle"
        for route in app.routes
    )


def test_bundle_serves_index_and_assets_with_the_loopback_token(
    bundle: Path, monkeypatch, isolated_token
) -> None:
    """Index and assets are reachable over loopback with the token."""
    monkeypatch.setenv(BUNDLE_ENV, str(bundle))
    client, headers = _client(monkeypatch)

    index = client.get("/index.html", headers=headers)
    assert index.status_code == 200
    assert "<html>" in index.text

    asset = client.get("/assets/app.js", headers=headers)
    assert asset.status_code == 200
    assert asset.text == "// built"


def test_bundle_rejects_an_unauthenticated_request(
    bundle: Path, monkeypatch, isolated_token
) -> None:
    """The bundle obeys the same loopback-token policy as the API."""
    monkeypatch.setenv(BUNDLE_ENV, str(bundle))
    client, _ = _client(monkeypatch)
    assert client.get("/index.html").status_code == 401


@pytest.mark.parametrize(
    "path",
    [
        "/api/v1/tts/synthesize",
        "/api/v1/stt/transcribe",
        "/api/v1/art/generate",
        "/api/v1/downloads/url",
    ],
)
def test_bundle_does_not_shadow_method_not_allowed(
    bundle: Path, monkeypatch, isolated_token, path: str
) -> None:
    """GET on a POST-only API path stays 405 with a bundle mounted."""
    monkeypatch.setenv(BUNDLE_ENV, str(bundle))
    client, headers = _client(monkeypatch)
    response = client.get(path, headers=headers)
    assert response.status_code == 405


def test_bundle_does_not_shadow_api_routes(
    bundle: Path, monkeypatch, isolated_token
) -> None:
    """A mounted bundle leaves the API paths answering as before."""
    monkeypatch.setenv(BUNDLE_ENV, str(bundle))
    client, headers = _client(monkeypatch)
    health = client.get("/api/v1/health", headers=headers)
    assert health.status_code == 200
    assert "status" in health.json()
    root = client.get("/", headers=headers)
    assert root.json() == {"status": "ready", "service": "airunner"}


def test_explicit_bundle_path_without_index_is_not_mounted(
    tmp_path, monkeypatch
) -> None:
    """An explicit path without an index document is not mounted."""
    monkeypatch.setenv(BUNDLE_ENV, str(tmp_path / "empty-choice"))
    assert bundle_directory() is None


def test_query_token_authenticates_the_entry_document(
    bundle: Path, monkeypatch, isolated_token
) -> None:
    """The surface's entry document is reachable with the query token.

    QtWebEngine navigates to the document before any interceptor-injected
    header can be relied on, so the host passes the loopback token as a
    query parameter -- the same credential and the same mechanism the
    WebSocket handshake already uses.
    """
    monkeypatch.setenv(BUNDLE_ENV, str(bundle))
    client, _ = _client(monkeypatch)
    token = loopback_token.get_or_create_loopback_token()

    allowed = client.get(f"/index.html?token={token}")
    assert allowed.status_code == 200

    denied = client.get("/index.html?token=wrong")
    assert denied.status_code == 401
