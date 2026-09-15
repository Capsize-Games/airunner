"""Unit tests for the per-user loopback token (GitHub issue #2033).

Proves:
- A second local process without the token receives 401 on API endpoints.
- Health endpoints stay open.
- The GUI daemon client sends the token on every request.
- The token file is created with 0600 permissions.
- ``AIRUNNER_INSECURE_NO_AUTH=1`` keeps the no-auth bypass.
- ``AIRUNNER_API_KEY`` semantics for non-loopback binds are unchanged.
"""

from __future__ import annotations

import asyncio
import stat
from unittest import mock

import httpx
import pytest

from airunner_services.api import loopback_token
from airunner_services.api.server import create_app
from airunner_services.daemon_client.gui_daemon_client import GuiDaemonClient
from airunner_services.runtimes.art_daemon_runtime_settings import (
    ArtDaemonRuntimeSettings,
)
from airunner_services.runtimes.sidecar_art_client import SidecarArtClient
from airunner_services.runtimes.sidecar_tts_client import SidecarTTSClient
from airunner_services.runtimes.tts_daemon_runtime_settings import (
    TTSDaemonRuntimeSettings,
)
from airunner_services.database import reset_engine, setup_database

_TOKEN_PATH = "/api/v1/llm/models"


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


@pytest.fixture()
def test_db(tmp_path, monkeypatch):
    """Point the ORM at a temp SQLite file and apply the schema.

    Mirrors the launcher pattern (setup_database) used by other DB-backed
    tests: the schema is only created via setup_database(), never by
    create_app() itself, so DB-backed routes need it up front.
    """
    db_url = f"sqlite:///{tmp_path / 'loopback-auth.sqlite'}"
    monkeypatch.setenv("AIRUNNER_DATABASE_URL", db_url)
    monkeypatch.setenv("AIRUNNER_DISABLE_DB_SETUP_CACHE", "1")
    reset_engine()
    setup_database()
    return db_url


@pytest.fixture()
def app(monkeypatch, test_db):
    """A no-API-key, no-insecure-bypass app instance."""
    monkeypatch.setenv("AIRUNNER_API_KEY", "")
    monkeypatch.setenv("AIRUNNER_INSECURE_NO_AUTH", "0")
    return create_app()


def _request(
    app,
    method: str,
    path: str,
    *,
    loopback: bool,
    headers: dict[str, str] | None = None,
) -> httpx.Response:
    """Issue one request against the ASGI app with a chosen client host."""
    client_addr = ("127.0.0.1", 55555) if loopback else ("192.0.2.1", 55555)
    transport = httpx.ASGITransport(app=app, client=client_addr)

    async def _run() -> httpx.Response:
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://127.0.0.1:55555",
            timeout=10.0,
        ) as client:
            return await client.request(method, path, headers=headers)

    return asyncio.run(_run())


def test_health_is_exempt(app, isolated_token) -> None:
    response = _request(app, "GET", "/api/v1/health", loopback=True)
    assert response.status_code == 200


def test_loopback_without_token_receives_401(app, isolated_token) -> None:
    response = _request(app, "GET", _TOKEN_PATH, loopback=True)
    assert response.status_code == 401


def test_loopback_with_wrong_token_receives_401(
    app, isolated_token
) -> None:
    response = _request(
        app,
        "GET",
        _TOKEN_PATH,
        loopback=True,
        headers={"X-Airunner-Token": "definitely-wrong"},
    )
    assert response.status_code == 401


def test_loopback_with_valid_token_is_authenticated(
    app, isolated_token
) -> None:
    token = loopback_token.get_or_create_loopback_token()
    response = _request(
        app,
        "GET",
        _TOKEN_PATH,
        loopback=True,
        headers={"X-Airunner-Token": token},
    )
    # Authenticated: the route runs (may 404/500) but must not be 401/403.
    assert response.status_code not in {401, 403}


def test_loopback_token_accepts_bearer_header(app, isolated_token) -> None:
    token = loopback_token.get_or_create_loopback_token()
    response = _request(
        app,
        "GET",
        _TOKEN_PATH,
        loopback=True,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code not in {401, 403}


def test_non_loopback_without_api_key_receives_401(
    app, isolated_token
) -> None:
    response = _request(app, "GET", _TOKEN_PATH, loopback=False)
    assert response.status_code == 401


def test_insecure_no_auth_bypasses_token(
    monkeypatch, isolated_token, test_db
) -> None:
    monkeypatch.setenv("AIRUNNER_API_KEY", "")
    monkeypatch.setenv("AIRUNNER_INSECURE_NO_AUTH", "1")
    app = create_app()
    response = _request(app, "GET", _TOKEN_PATH, loopback=True)
    assert response.status_code not in {401, 403}


def test_api_key_still_required_for_non_loopback(
    monkeypatch, isolated_token, test_db
) -> None:
    monkeypatch.setenv("AIRUNNER_API_KEY", "secret-key-123")
    monkeypatch.setenv("AIRUNNER_INSECURE_NO_AUTH", "0")
    app = create_app()
    without_key = _request(app, "GET", _TOKEN_PATH, loopback=False)
    with_key = _request(
        app,
        "GET",
        _TOKEN_PATH,
        loopback=False,
        headers={"X-API-Key": "secret-key-123"},
    )
    assert without_key.status_code == 401
    assert with_key.status_code not in {401, 403}


def test_token_file_created_with_0600_permissions(isolated_token) -> None:
    token = loopback_token.get_or_create_loopback_token()
    assert token
    assert isolated_token.exists()
    mode = stat.S_IMODE(isolated_token.stat().st_mode)
    assert mode == 0o600, f"token file mode was {oct(mode)}"


def test_token_is_stable_across_reads(isolated_token) -> None:
    first = loopback_token.get_or_create_loopback_token()
    second = loopback_token.get_or_create_loopback_token()
    assert first == second


def test_gui_client_sends_token_on_every_request(tmp_path) -> None:
    session = mock.MagicMock()
    response = mock.MagicMock()
    response.raise_for_status.return_value = None
    response.json.return_value = {}
    response.status_code = 200
    session.request.return_value = response

    with mock.patch.object(
        loopback_token, "loopback_token_path"
    ) as fake_path:
        fake_path.return_value = tmp_path / "loopback_token"
        loopback_token._cache_loaded = False
        loopback_token._cached_token = None
        client = GuiDaemonClient(
            config_path=tmp_path / "daemon.yaml",
            session=session,
            auto_start=False,
        )
        with mock.patch.object(client, "ensure_connected", return_value=True):
            client._request("GET", "/api/v1/llm/models")

    _, kwargs = session.request.call_args
    headers = kwargs.get("headers") or {}
    assert headers.get("X-Airunner-Token") == client._loopback_token
    assert client._loopback_token == loopback_token.get_or_create_loopback_token()


def test_sidecar_art_client_sends_token_on_every_request(tmp_path) -> None:
    session = mock.MagicMock()
    response = mock.MagicMock()
    response.raise_for_status.return_value = None
    response.json.return_value = {}
    response.status_code = 200
    session.request.return_value = response

    launcher = mock.MagicMock()
    launcher.api_base_url = "http://127.0.0.1:8190/api/v1/art"
    launcher.endpoint = "http://127.0.0.1:8190"
    settings = ArtDaemonRuntimeSettings(
        host="127.0.0.1",
        port=8190,
        base_daemon_config_path=None,
        art_model_path=None,
        art_model_version=None,
        art_scheduler=None,
        startup_timeout_seconds=90.0,
        request_timeout_seconds=10.0,
        invocation_timeout_seconds=1800.0,
        status_poll_interval_seconds=0.10,
    )

    with mock.patch.object(
        loopback_token, "loopback_token_path"
    ) as fake_path:
        fake_path.return_value = tmp_path / "loopback_token"
        loopback_token._cache_loaded = False
        loopback_token._cached_token = None
        client = SidecarArtClient(
            settings=settings,
            launcher=launcher,
            session=session,
        )
        client._request("GET", "/status/abc")

    _, kwargs = session.request.call_args
    headers = kwargs.get("headers") or {}
    expected = loopback_token.get_or_create_loopback_token()
    assert headers.get("X-Airunner-Token") == expected
    assert client._loopback_headers() == {"X-Airunner-Token": expected}


def test_sidecar_tts_client_sends_token_on_every_request(tmp_path) -> None:
    session = mock.MagicMock()
    response = mock.MagicMock()
    response.raise_for_status.return_value = None
    response.json.return_value = {}
    response.status_code = 200
    session.request.return_value = response

    launcher = mock.MagicMock()
    launcher.api_base_url = "http://127.0.0.1:8191/api/v1/tts"
    launcher.endpoint = "http://127.0.0.1:8191"
    settings = TTSDaemonRuntimeSettings(
        host="127.0.0.1",
        port=8191,
        base_daemon_config_path=None,
        tts_model_path=None,
        tts_model_type=None,
        startup_timeout_seconds=90.0,
        request_timeout_seconds=120.0,
    )

    with mock.patch.object(
        loopback_token, "loopback_token_path"
    ) as fake_path:
        fake_path.return_value = tmp_path / "loopback_token"
        loopback_token._cache_loaded = False
        loopback_token._cached_token = None
        client = SidecarTTSClient(
            settings=settings,
            launcher=launcher,
            session=session,
        )
        client._request(
            "GET",
            f"{launcher.endpoint}/api/v1/daemon/runtimes/tts",
        )

    _, kwargs = session.request.call_args
    headers = kwargs.get("headers") or {}
    expected = loopback_token.get_or_create_loopback_token()
    assert headers.get("X-Airunner-Token") == expected
    assert client._loopback_headers() == {"X-Airunner-Token": expected}
