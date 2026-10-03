"""Regression tests for issue #2229.

A version-only art generation request must resolve to an installed
checkpoint of that version, and a request naming a model that is not
available locally must be rejected with a 4xx. Either way the request
must never reach the worker only to stall until the 30-minute timeout
and block later jobs.
"""

from __future__ import annotations

import importlib
import os
import shutil
import tempfile
import time
from pathlib import Path
from typing import Iterator

import pytest
from fastapi.testclient import TestClient

from airunner_services.api.server import create_app

_REPO_ROOT = Path(__file__).resolve().parents[2]
_ART_ROUTE = "/api/v1/art/generate"
_VERSION = "Z-Image Turbo"


class _FakeApi:
    """Minimal app surface used by the route tests."""

    def __init__(self) -> None:
        self.llm = None

    def emit_signal(self, _code, _data=None) -> None:
        """Ignore signal emissions during route tests."""

    def worker_response(self, code, message) -> None:
        """Ignore worker responses during route tests."""


@pytest.fixture
def model_base() -> Iterator[Path]:
    """Create a scratch art-models base dir under repo tmp/."""
    base = _REPO_ROOT / "tmp" / "art_model_tests"
    base.mkdir(parents=True, exist_ok=True)
    created = Path(tempfile.mkdtemp(prefix="models_", dir=base))
    yield created
    shutil.rmtree(created, ignore_errors=True)


def _route_client() -> TestClient:
    """Return a TestClient bound to a fresh FastAPI app."""
    os.environ["AIRUNNER_INSECURE_NO_AUTH"] = "1"
    app = create_app(
        allowed_origins=["http://localhost"],
        enable_cors=False,
        app_instance=_FakeApi(),
    )
    return TestClient(app)


def _patch_downstream(
    monkeypatch: pytest.MonkeyPatch,
    routes,
    captured: dict,
) -> None:
    """Replace the route's downstream work with recording fakes."""

    async def _spy_unload(*_args, **_kwargs) -> None:
        captured["unload_calls"].append(True)

    async def _spy_run(_tracker, _job_id, art_request, _client) -> None:
        captured["run_calls"].append(art_request)

    class _FakeTracker:
        async def create_job(self, metadata=None):
            captured["job_metadata"].append(metadata)
            return "job-1"

        async def update_progress(self, *_args, **_kwargs):
            return None

    monkeypatch.setattr(routes, "unload_llm_before_art", _spy_unload)
    monkeypatch.setattr(
        routes, "require_runtime_registry", lambda _req: object()
    )
    monkeypatch.setattr(routes, "resolve_art_client", lambda _reg: object())
    monkeypatch.setattr(routes, "JobTracker", _FakeTracker)
    monkeypatch.setattr(routes, "run_art_job", _spy_run)


def _patch_model_scan(
    monkeypatch: pytest.MonkeyPatch, model_base: Path
) -> None:
    """Point model resolution at a scratch base dir without DB access."""
    resolution = importlib.import_module(
        "airunner_services.api.routes.art_generation_model"
    )
    monkeypatch.setattr(resolution, "art_model_base_dir", lambda: model_base)
    monkeypatch.setattr(resolution, "generator_settings_record", lambda: None)


def _run_art_request(monkeypatch, model_base, payload) -> tuple:
    """POST one art request and return (response, captured)."""
    routes = importlib.import_module(
        "airunner_services.api.routes.art_generation_start_routes"
    )
    captured: dict = {
        "unload_calls": [],
        "run_calls": [],
        "job_metadata": [],
    }
    _patch_downstream(monkeypatch, routes, captured)
    _patch_model_scan(monkeypatch, model_base)
    with _route_client() as client:
        response = client.post(_ART_ROUTE, json=payload)
        deadline = time.monotonic() + 5.0
        while not captured["run_calls"] and time.monotonic() < deadline:
            if response.status_code != 200:
                break
            time.sleep(0.05)
    return response, captured


def _install_checkpoint(model_base: Path) -> Path:
    """Install one fake checkpoint for the test version."""
    action_dir = model_base / _VERSION / "txt2img"
    action_dir.mkdir(parents=True, exist_ok=True)
    checkpoint = action_dir / "model.safetensors"
    checkpoint.write_bytes(b"fake-checkpoint")
    return checkpoint


def test_version_only_resolves_to_installed_checkpoint(
    model_base: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A version with no model uses the installed checkpoint."""
    checkpoint = _install_checkpoint(model_base)
    response, captured = _run_art_request(
        monkeypatch,
        model_base,
        {"prompt": "a grey sphere", "version": _VERSION},
    )
    assert response.status_code == 200
    assert response.json()["job_id"] == "job-1"
    assert captured["job_metadata"][0]["model"] == str(checkpoint)
    assert captured["run_calls"][0].model == str(checkpoint)


def test_version_only_without_checkpoint_is_rejected(
    model_base: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A version with no checkpoint fails before touching the worker."""
    response, captured = _run_art_request(
        monkeypatch,
        model_base,
        {"prompt": "a grey sphere", "version": _VERSION},
    )
    assert response.status_code == 404
    assert response.json()["detail"] == (
        f"No installed checkpoint for art version '{_VERSION}'"
    )
    assert captured["unload_calls"] == []
    assert captured["job_metadata"] == []
    assert captured["run_calls"] == []


def test_unknown_version_is_rejected(
    model_base: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An unknown version never silently becomes another model."""
    _install_checkpoint(model_base)
    response, captured = _run_art_request(
        monkeypatch,
        model_base,
        {"prompt": "a grey sphere", "version": "No Such Version"},
    )
    assert response.status_code == 404
    assert captured["unload_calls"] == []
    assert captured["run_calls"] == []


def test_missing_model_path_is_rejected(
    model_base: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A model path that does not exist fails before the worker."""
    missing = str(model_base / "missing.safetensors")
    with caplog.at_level("DEBUG"):
        response, captured = _run_art_request(
            monkeypatch,
            model_base,
            {"prompt": "a grey sphere", "model": missing},
        )
    assert response.status_code == 400
    assert response.json()["detail"] == (
        f"Art model '{missing}' is not available locally"
    )
    assert captured["unload_calls"] == []
    assert captured["job_metadata"] == []
    assert captured["run_calls"] == []
    assert all(
        missing not in record.getMessage() for record in caplog.records
    )


def test_huggingface_id_model_is_rejected(
    model_base: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A registry id is not a loadable local model."""
    model = "Tongyi-MAI/Z-Image-Turbo"
    response, captured = _run_art_request(
        monkeypatch,
        model_base,
        {"prompt": "a grey sphere", "model": model},
    )
    assert response.status_code == 400
    assert captured["unload_calls"] == []
    assert captured["run_calls"] == []


def test_existing_model_path_passes_through(
    model_base: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An explicitly sent checkpoint keeps working unchanged."""
    checkpoint = _install_checkpoint(model_base)
    response, captured = _run_art_request(
        monkeypatch,
        model_base,
        {
            "prompt": "a grey sphere",
            "model": str(checkpoint),
            "version": _VERSION,
        },
    )
    assert response.status_code == 200
    assert captured["job_metadata"][0]["model"] == str(checkpoint)
    assert captured["run_calls"][0].model == str(checkpoint)


def test_neither_model_nor_version_passes_through(
    model_base: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A bare request keeps the existing server-default behavior."""
    response, captured = _run_art_request(
        monkeypatch,
        model_base,
        {"prompt": "a grey sphere"},
    )
    assert response.status_code == 200
    assert captured["job_metadata"][0]["model"] is None
    assert captured["run_calls"][0].model is None
