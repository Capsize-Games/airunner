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
from collections.abc import Callable, Coroutine
from pathlib import Path
from types import ModuleType
from typing import Any, Iterator

import pytest
from fastapi.testclient import TestClient
from httpx import Response

from airunner_services.api.routes.art_contracts import GenerationRequest
from airunner_services.api.server import create_app

_REPO_ROOT = Path(__file__).resolve().parents[2]
_ART_ROUTE = "/api/v1/art/generate"
_VERSION = "Z-Image Turbo"


class _FakeApi:
    """Minimal app surface used by the route tests."""

    def __init__(self) -> None:
        self.llm = None

    def emit_signal(self, _code: object, _data: object = None) -> None:
        """Ignore signal emissions during route tests."""

    def worker_response(self, code: object, message: object) -> None:
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


def _fake_tracker_class(captured: dict[str, list]) -> type:
    """Return a JobTracker fake recording one created job."""

    class _FakeTracker:
        """Record job creation without tracker side effects."""

        async def create_job(self, metadata: dict | None = None) -> str:
            """Record one job metadata payload."""
            captured["job_metadata"].append(metadata)
            return "job-1"

        async def update_progress(
            self, *_args: object, **_kwargs: object
        ) -> None:
            """Ignore progress updates during route tests."""
            return None

    return _FakeTracker


def _unload_spy(
    captured: dict[str, list],
) -> Callable[..., Coroutine[Any, Any, None]]:
    """Return an unload fake recording its calls."""

    async def _spy(*_args: object, **_kwargs: object) -> None:
        captured["unload_calls"].append(True)

    return _spy


def _run_spy(
    captured: dict[str, list],
) -> Callable[..., Coroutine[Any, Any, None]]:
    """Return a run fake recording forwarded requests."""

    async def _spy(
        _tracker: object, _job_id: str,
        art_request: GenerationRequest, _client: object,
    ) -> None:
        captured["run_calls"].append(art_request)

    return _spy


def _patch_downstream(
    monkeypatch: pytest.MonkeyPatch,
    routes: ModuleType,
    captured: dict[str, list],
) -> None:
    """Replace the route's downstream work with recording fakes."""
    monkeypatch.setattr(
        routes, "unload_llm_before_art", _unload_spy(captured)
    )
    monkeypatch.setattr(
        routes, "require_runtime_registry", lambda _req: object()
    )
    monkeypatch.setattr(routes, "resolve_art_client", lambda _reg: object())
    monkeypatch.setattr(routes, "JobTracker", _fake_tracker_class(captured))
    monkeypatch.setattr(routes, "run_art_job", _run_spy(captured))


def _patch_model_scan(
    monkeypatch: pytest.MonkeyPatch, model_base: Path
) -> None:
    """Point model resolution at a scratch base dir without DB access."""
    resolution = importlib.import_module(
        "airunner_services.api.routes.art_generation_model"
    )
    monkeypatch.setattr(resolution, "art_model_base_dir", lambda: model_base)
    monkeypatch.setattr(resolution, "generator_settings_record", lambda: None)


def _empty_captured() -> dict[str, list]:
    """Return empty side-effect captures for one request."""
    return {"unload_calls": [], "run_calls": [], "job_metadata": []}


def _await_forwarded_request(
    response: Response, captured: dict[str, list]
) -> None:
    """Wait for the background run task to record its request."""
    deadline = time.monotonic() + 5.0
    while not captured["run_calls"] and time.monotonic() < deadline:
        if response.status_code != 200:
            break
        time.sleep(0.05)


def _run_art_request(
    monkeypatch: pytest.MonkeyPatch,
    model_base: Path,
    payload: dict[str, object],
) -> tuple[Response, dict[str, list]]:
    """POST one art request and return (response, captured)."""
    routes = importlib.import_module(
        "airunner_services.api.routes.art_generation_start_routes"
    )
    captured = _empty_captured()
    _patch_downstream(monkeypatch, routes, captured)
    _patch_model_scan(monkeypatch, model_base)
    with _route_client() as client:
        response = client.post(_ART_ROUTE, json=payload)
        _await_forwarded_request(response, captured)
    return response, captured


def _install_checkpoint(
    model_base: Path,
    action: str = "txt2img",
    name: str = "model.safetensors",
) -> Path:
    """Install one fake checkpoint for the test version."""
    action_dir = model_base / _VERSION / action
    action_dir.mkdir(parents=True, exist_ok=True)
    checkpoint = action_dir / name
    checkpoint.write_bytes(b"fake-checkpoint")
    return checkpoint


def _assert_missing_model_rejection(
    response: Response, missing: str
) -> None:
    """Assert one 400 rejection for a missing model path."""
    assert response.status_code == 400
    assert response.json()["detail"] == (
        f"Art model '{missing}' is not available locally"
    )


def _assert_missing_not_logged(
    caplog: pytest.LogCaptureFixture, missing: str
) -> None:
    """Assert one rejected model path never reached the logs."""
    assert all(
        missing not in record.getMessage() for record in caplog.records
    )


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
    assert captured["job_metadata"][0]["version"] == _VERSION
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


def test_traversal_version_is_rejected(
    model_base: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A version escaping the model tree is rejected outright."""
    response, captured = _run_art_request(
        monkeypatch,
        model_base,
        {"prompt": "a grey sphere", "version": "../../etc"},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid art version '../../etc'"
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
    _assert_missing_model_rejection(response, missing)
    assert captured["unload_calls"] == []
    assert captured["job_metadata"] == []
    assert captured["run_calls"] == []
    _assert_missing_not_logged(caplog, missing)


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


def test_invalid_model_with_valid_version_is_rejected(
    model_base: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An explicit bad model wins over a resolvable version."""
    _install_checkpoint(model_base)
    missing = str(model_base / "missing.safetensors")
    response, captured = _run_art_request(
        monkeypatch,
        model_base,
        {"prompt": "a grey sphere", "model": missing,
         "version": _VERSION},
    )
    assert response.status_code == 400
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


def test_existing_model_directory_passes_through(
    model_base: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An explicitly sent diffusers directory keeps working."""
    bundle = model_base / "bundle"
    bundle.mkdir(parents=True, exist_ok=True)
    (bundle / "model_index.json").write_text("{}", encoding="utf-8")
    response, captured = _run_art_request(
        monkeypatch,
        model_base,
        {"prompt": "a grey sphere", "model": str(bundle)},
    )
    assert response.status_code == 200
    assert captured["run_calls"][0].model == str(bundle)


def test_whitespace_model_falls_back_to_version(
    model_base: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A blank model is treated as no model."""
    checkpoint = _install_checkpoint(model_base)
    response, captured = _run_art_request(
        monkeypatch,
        model_base,
        {"prompt": "a grey sphere", "model": "  ", "version": _VERSION},
    )
    assert response.status_code == 200
    assert captured["run_calls"][0].model == str(checkpoint)


def test_version_resolution_honors_pipeline(
    model_base: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A requested pipeline selects its own action directory."""
    _install_checkpoint(model_base, action="txt2img", name="txt.safetensors")
    expected = _install_checkpoint(
        model_base, action="img2img", name="img.safetensors"
    )
    response, captured = _run_art_request(
        monkeypatch,
        model_base,
        {"prompt": "a grey sphere", "version": _VERSION,
         "pipeline": "img2img"},
    )
    assert response.status_code == 200
    assert captured["run_calls"][0].model == str(expected)


def test_unknown_pipeline_falls_back(
    model_base: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An unknown pipeline falls back like the runtime default."""
    checkpoint = _install_checkpoint(model_base)
    response, captured = _run_art_request(
        monkeypatch,
        model_base,
        {"prompt": "a grey sphere", "version": _VERSION,
         "pipeline": "bogus"},
    )
    assert response.status_code == 200
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
