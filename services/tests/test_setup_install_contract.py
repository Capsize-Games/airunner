"""Verify administrative setup outcomes without downloads or model loads."""

import json
import asyncio
import sys
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from airunner_services.api.routes import setup
from airunner_services.api.routes.setup_nltk import install_nltk_data


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setenv("AIRUNNER_ADMIN_KEY", "test-admin")
    monkeypatch.setattr(setup, "is_offline_mode", lambda: False)
    monkeypatch.setattr(setup, "_allowed_base_roots", lambda: [str(tmp_path)])
    monkeypatch.setattr(setup, "_create_directories", lambda path: [])

    async def install_data():
        return ["fixture"]

    monkeypatch.setattr(setup, "_install_nltk_data", install_data)
    app = FastAPI()
    app.include_router(setup.router, prefix="/api/v1")
    return TestClient(app), {"base_path": str(tmp_path)}


def _post(client, payload):
    return client.post(
        "/api/v1/install", json=payload,
        headers={"x-admin-key": "test-admin"},
    )


def _events(response):
    assert response.status_code == 200
    return [
        json.loads(line[6:]) for line in response.text.splitlines()
        if line.startswith("data: ")
    ]


def test_install_requires_existing_admin_key(client):
    http, payload = client
    assert http.post("/api/v1/install", json=payload).status_code == 403


def test_offline_install_rejected_before_work(client, monkeypatch):
    http, payload = client
    monkeypatch.setattr(setup, "is_offline_mode", lambda: True)
    assert _post(http, payload).status_code == 403


def test_missing_download_service_is_not_success(client, monkeypatch):
    http, payload = client
    monkeypatch.setattr(setup, "_resolve_download_jobs", lambda _: [{}])
    assert _post(http, payload).status_code == 503


def test_queue_failure_is_partial_and_never_completed(client, monkeypatch):
    http, payload = client
    jobs = [{"repo_id": key, "model_type": "llm"} for key in ("a", "b")]
    monkeypatch.setattr(setup, "_resolve_download_jobs", lambda _: jobs)

    async def start(**kwargs):
        if kwargs["repo_id"] == "b":
            raise RuntimeError("private failure detail")
        return "job-1"

    http.app.state.download_job_service = SimpleNamespace(
        start_huggingface_download=start
    )
    events = _events(_post(http, payload))
    assert events[-1]["status"] == "partial"
    assert events[-1]["queued"] == events[-1]["failed"] == 1
    assert all(event["status"] != "completed" for event in events)
    assert "private failure detail" not in json.dumps(events)


def test_successful_queue_is_not_completed_download(client, monkeypatch):
    http, payload = client
    jobs = [{"repo_id": "a", "model_type": "llm"}]
    monkeypatch.setattr(setup, "_resolve_download_jobs", lambda _: jobs)

    async def start(**kwargs):
        return "job-1"

    http.app.state.download_job_service = SimpleNamespace(
        start_huggingface_download=start
    )
    assert _events(_post(http, payload))[-1]["status"] == "queued"


def test_nltk_failure_is_terminal(client, monkeypatch):
    http, payload = client

    async def fail():
        raise RuntimeError("private error")

    monkeypatch.setattr(setup, "_install_nltk_data", fail)
    assert _events(_post(http, payload))[-1]["status"] == "failed"


def test_unknown_model_family_rejected(client):
    http, payload = client
    payload["enabled_models"] = {"missing_provider": True}
    assert _post(http, payload).status_code == 422


def test_current_art_catalog_is_selected(monkeypatch):
    monkeypatch.setattr(setup, "model_bootstrap_data", [{
        "path": "fixture/art", "model_type": "art", "category": "zimage",
    }])
    assert setup._resolve_download_jobs({"stable_diffusion": True}) == [{
        "repo_id": "fixture/art", "model_type": "art",
        "version": "", "pipeline_action": "",
    }]


def test_nltk_false_return_is_not_reported_installed(monkeypatch):
    monkeypatch.setitem(
        sys.modules, "nltk", SimpleNamespace(download=lambda *a, **kw: False)
    )
    with pytest.raises(RuntimeError, match="NLTK data installation failed"):
        asyncio.run(install_nltk_data())
