"""Tests for the daemon-hosted desktop chat client bundle (#2230, B4a).

The bundle is optional and must not change daemon routing when it is
absent; when present it must be reachable over loopback under the same
loopback-token policy as the rest of the API.
"""

from __future__ import annotations

from pathlib import Path

import pytest
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
    """An unset or index-less directory yields no bundle."""
    monkeypatch.delenv(BUNDLE_ENV, raising=False)
    assert bundle_directory() is None

    empty = tmp_path / "empty"
    empty.mkdir()
    monkeypatch.setenv(BUNDLE_ENV, str(empty))
    assert bundle_directory() is None


def test_bundle_directory_resolves_the_built_bundle(
    bundle: Path, monkeypatch
) -> None:
    """A directory with an index file resolves to itself."""
    monkeypatch.setenv(BUNDLE_ENV, str(bundle))
    assert bundle_directory() == bundle


def test_bundle_is_not_mounted_when_unconfigured(
    monkeypatch, isolated_token
) -> None:
    """Daemon routing is unchanged without a configured bundle."""
    monkeypatch.delenv(BUNDLE_ENV, raising=False)
    app = create_app()
    assert mount_client_bundle(app) is False
    client, _ = _client(monkeypatch)
    assert client.get("/index.html").status_code == 401


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
