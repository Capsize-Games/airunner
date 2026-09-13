"""Regression tests for release issue O02.

Proves the O01 offline-egress policy is applied to user-triggered
downloads (HuggingFace, CivitAI) and other network tools reachable
under services/src/airunner_services/downloads/: a disabled provider
fails immediately with an actionable message before any tracker job,
background thread, or network transport call, and the underlying
network function is never reached.

Uses only fake/mocked transports (mock.patch on requests.get/Session)
and a temporary SQLite database — no real model/network access.
"""

from __future__ import annotations

import asyncio
from unittest import mock

import pytest
from starlette.testclient import TestClient

from airunner_services.api import loopback_token
from airunner_services.api import server as server_module
from airunner_services.api.server import create_app
from airunner_services.database import reset_engine, setup_database
from airunner_services.downloads.job_service import DownloadJobService
from airunner_services.downloads.policy import (
    SERVICE_CIVITAI_KEY,
    SERVICE_DUCKDUCKGO_KEY,
    SERVICE_HUGGINGFACE_KEY,
    SERVICE_OPENAI_KEY,
    SERVICE_OPENMETEO_KEY,
    SERVICE_OPENROUTER_KEY,
    is_service_allowed,
)
from airunner_services.downloads.service import (
    ProviderDownloadDisabled,
    download_civitai_file,
    fetch_civitai_browser_model_info,
    fetch_civitai_model_info,
    require_provider_allowed,
    search_civitai_models,
)

_ALL_SERVICE_KEYS = (
    SERVICE_HUGGINGFACE_KEY,
    SERVICE_CIVITAI_KEY,
    SERVICE_DUCKDUCKGO_KEY,
    SERVICE_OPENMETEO_KEY,
    SERVICE_OPENROUTER_KEY,
    SERVICE_OPENAI_KEY,
)


@pytest.fixture()
def offline(monkeypatch):
    import airunner_common.settings as common_settings

    monkeypatch.setattr(common_settings, "AIRUNNER_OFFLINE_MODE", True)


@pytest.fixture()
def online(monkeypatch):
    import airunner_common.settings as common_settings

    monkeypatch.setattr(common_settings, "AIRUNNER_OFFLINE_MODE", False)


# --- policy.is_service_allowed(): offline overrides every service key ---


def test_every_service_key_denied_while_offline(offline) -> None:
    for key in _ALL_SERVICE_KEYS:
        assert is_service_allowed(key) is False


def test_service_keys_use_their_own_default_once_online(online) -> None:
    # HuggingFace/CivitAI default to allowed; Open-Meteo defaults to denied.
    assert is_service_allowed(SERVICE_HUGGINGFACE_KEY) is True
    assert is_service_allowed(SERVICE_CIVITAI_KEY) is True
    assert is_service_allowed(SERVICE_OPENMETEO_KEY) is False


# --- service.require_provider_allowed() / ProviderDownloadDisabled ---


def test_require_provider_allowed_raises_with_offline_message(offline) -> None:
    with pytest.raises(ProviderDownloadDisabled, match="offline mode"):
        require_provider_allowed("huggingface")


def test_require_provider_allowed_passes_when_online_and_allowed(online) -> None:
    require_provider_allowed("huggingface")  # must not raise


def test_require_provider_allowed_unknown_provider_still_raises() -> None:
    with pytest.raises(ValueError):
        require_provider_allowed("not-a-real-provider")


# --- service.py facade functions never reach the network when blocked ---


def test_fetch_civitai_model_info_blocked_offline_never_calls_network(
    offline,
) -> None:
    with mock.patch(
        "airunner_services.downloads.service.fetch_model_info_for_url"
    ) as fetch:
        with pytest.raises(ProviderDownloadDisabled):
            fetch_civitai_model_info("https://civitai.com/models/1")
        fetch.assert_not_called()


def test_search_civitai_models_blocked_offline_never_calls_network(
    offline,
) -> None:
    with mock.patch(
        "airunner_services.downloads.service.search_models"
    ) as search:
        with pytest.raises(ProviderDownloadDisabled):
            search_civitai_models("anime")
        search.assert_not_called()


def test_fetch_civitai_browser_model_info_blocked_offline_never_calls_network(
    offline,
) -> None:
    with mock.patch(
        "airunner_services.downloads.service.fetch_browser_model_info"
    ) as fetch:
        with pytest.raises(ProviderDownloadDisabled):
            fetch_civitai_browser_model_info("123")
        fetch.assert_not_called()


def test_download_civitai_file_blocked_offline_never_calls_network(
    offline,
) -> None:
    with mock.patch(
        "airunner_services.downloads.service.civitai_download_file"
    ) as download:
        with pytest.raises(ProviderDownloadDisabled):
            download_civitai_file()
        download.assert_not_called()


# --- job_service.py: blocked before any tracker job or thread starts ---


def test_start_huggingface_download_blocked_offline_creates_no_job(
    offline,
) -> None:
    service = DownloadJobService()
    with mock.patch.object(
        service, "_start_job", wraps=service._start_job
    ) as start_job:
        with pytest.raises(ProviderDownloadDisabled):
            asyncio.run(service.start_huggingface_download("some/repo"))
        start_job.assert_not_called()


def test_start_civitai_model_download_blocked_offline_creates_no_job(
    offline, tmp_path
) -> None:
    service = DownloadJobService()
    with mock.patch.object(
        service, "_start_job", wraps=service._start_job
    ) as start_job:
        with pytest.raises(ProviderDownloadDisabled):
            asyncio.run(
                service.start_civitai_model_download(
                    "https://civitai.com/models/1",
                    output_dir=str(tmp_path),
                )
            )
        start_job.assert_not_called()


def test_start_huggingface_download_proceeds_when_online(online) -> None:
    service = DownloadJobService()
    with mock.patch.object(service, "_start_job", return_value="job-1") as start_job:
        job_id = asyncio.run(service.start_huggingface_download("some/repo"))
        assert job_id == "job-1"
        start_job.assert_called_once()


# --- HTTP route level: fake transport, zero external attempts, actionable 400 ---


@pytest.fixture()
def isolated_token(tmp_path, monkeypatch):
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
    db_url = f"sqlite:///{tmp_path / 'release-o02.sqlite'}"
    monkeypatch.setenv("AIRUNNER_DATABASE_URL", db_url)
    monkeypatch.setenv("AIRUNNER_DISABLE_DB_SETUP_CACHE", "1")
    reset_engine()
    setup_database()
    return db_url


@pytest.fixture()
def app(monkeypatch, isolated_token, test_db, offline):
    monkeypatch.setenv("AIRUNNER_API_KEY", "")
    monkeypatch.setenv("AIRUNNER_INSECURE_NO_AUTH", "0")
    monkeypatch.setattr(server_module, "is_loopback_request", lambda conn: True)
    return create_app()


def _token() -> str:
    return loopback_token.get_or_create_loopback_token()


def test_huggingface_route_blocked_offline_with_zero_transport_attempts(
    app,
) -> None:
    client = TestClient(app)
    with mock.patch("requests.Session.request") as session_request:
        response = client.post(
            "/api/v1/downloads/huggingface",
            json={"repo_id": "some/repo"},
            headers={"X-Airunner-Token": _token()},
        )
        session_request.assert_not_called()

    assert response.status_code == 400
    assert "offline mode" in response.json()["detail"]


def test_civitai_info_route_blocked_offline_with_zero_transport_attempts(
    app,
) -> None:
    client = TestClient(app)
    with mock.patch("requests.Session.request") as session_request:
        response = client.post(
            "/api/v1/downloads/civitai/info",
            json={"url": "https://civitai.com/models/1"},
            headers={"X-Airunner-Token": _token()},
        )
        session_request.assert_not_called()

    assert response.status_code == 400
    assert "offline mode" in response.json()["detail"]
