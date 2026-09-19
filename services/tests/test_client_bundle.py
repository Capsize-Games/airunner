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
    BUNDLE_SUBDIR,
    BUILD_ROOT_ENV,
    bundle_directory,
    mount_client_bundle,
    packaged_bundle_directory,
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


@pytest.fixture(autouse=True)
def isolated_build_root(tmp_path, monkeypatch) -> Path:
    """Keep the machine's real release build directory out of these tests.

    ``packaged_bundle_directory()`` falls back to the owner's build output
    directory, which a release or a local packaging run may have
    populated. Pinning it to an empty temp root makes every test here
    depend only on what it sets up itself.
    """
    root = tmp_path / "build-root"
    root.mkdir()
    monkeypatch.setenv(BUILD_ROOT_ENV, str(root))
    return root


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


def test_packaged_bundle_is_discovered_without_any_env(
    tmp_path, monkeypatch
) -> None:
    """A release install finds its surface with no environment set.

    This is the release-time contract: ``AIRUNNER_CLIENT_BUNDLE`` stays
    unset, and the bundle is found in the designated build output
    directory because the packaging step placed it there.
    """
    monkeypatch.delenv(BUNDLE_ENV, raising=False)
    build_root = tmp_path / "builds"
    packaged = build_root / BUNDLE_SUBDIR
    packaged.mkdir(parents=True)
    (packaged / "index.html").write_text("<html></html>", encoding="utf-8")
    monkeypatch.setenv(BUILD_ROOT_ENV, str(build_root))

    assert packaged_bundle_directory() == packaged
    assert bundle_directory() == packaged


def test_packaged_bundle_is_absent_before_a_release_build(
    tmp_path, monkeypatch
) -> None:
    """An unpackaged build root yields no bundle, not a broken mount."""
    monkeypatch.delenv(BUNDLE_ENV, raising=False)
    monkeypatch.setenv(BUILD_ROOT_ENV, str(tmp_path / "nothing-built"))
    assert bundle_directory() is None


def test_explicit_bundle_env_does_not_fall_back(tmp_path, monkeypatch) -> None:
    """An explicit but empty path is authoritative, not a hint."""
    monkeypatch.setenv(BUNDLE_ENV, str(tmp_path / "empty-choice"))
    build_root = tmp_path / "builds"
    packaged = build_root / BUNDLE_SUBDIR
    packaged.mkdir(parents=True)
    (packaged / "index.html").write_text("<html></html>", encoding="utf-8")
    monkeypatch.setenv(BUILD_ROOT_ENV, str(build_root))

    assert bundle_directory() is None


def test_packaged_bundle_serves_the_surface(
    tmp_path, monkeypatch, isolated_token
) -> None:
    """The packaged location is mountable exactly like the explicit one."""
    monkeypatch.delenv(BUNDLE_ENV, raising=False)
    build_root = tmp_path / "builds"
    packaged = build_root / BUNDLE_SUBDIR
    packaged.mkdir(parents=True)
    (packaged / "index.html").write_text("<html>hi</html>", encoding="utf-8")
    monkeypatch.setenv(BUILD_ROOT_ENV, str(build_root))

    client, headers = _client(monkeypatch)
    response = client.get("/index.html", headers=headers)
    assert response.status_code == 200
    assert "hi" in response.text


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
