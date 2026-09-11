"""Integration tests for the content-safety input gate.

Every token used here is synthetic and neutral. No real policy term
appears in this file, and no assertion inspects the contents of a log
record or response body beyond checking that the synthetic input text is
absent.

Policy data is supplied through the matcher's own
``AIRUNNER_CONTENT_SAFETY_DATA`` env override, pointing at a temp file
whose lines are produced by the matcher's ``candidate_hashes`` helper.
"""

from __future__ import annotations

import importlib
import json
import logging
import os
import shutil
import tempfile
from pathlib import Path
from types import SimpleNamespace
from typing import Iterator

import pytest
from fastapi.testclient import TestClient

from airunner_services import content_safety_gate as gate
from airunner_services.api.server import create_app
from airunner_services.content_safety import candidate_hashes, policy_data

_REPO_ROOT = Path(__file__).resolve().parents[2]
_ART_ROUTE = "/api/v1/art/generate"

# A single invented, neutral token. It is not a policy term anywhere; the
# tests hash it locally to exercise the match path.
_SYNTHETIC = "zorbblesprocket"


# --------------------------------------------------------------------------
# Fixtures
# --------------------------------------------------------------------------


@pytest.fixture
def policy_dir() -> Iterator[Path]:
    """Create a scratch dir under the (gitignored) repo-local tmp/ tree."""
    base = _REPO_ROOT / "tmp" / "content_safety_tests"
    base.mkdir(parents=True, exist_ok=True)
    created = Path(tempfile.mkdtemp(prefix="gate_", dir=base))
    yield created
    shutil.rmtree(created, ignore_errors=True)


@pytest.fixture(autouse=True)
def _clean_policy_cache(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.delenv(policy_data.POLICY_DATA_ENV_VAR, raising=False)
    policy_data.reset_cache()
    yield
    policy_data.reset_cache()


def _load_synthetic_policy(
    policy_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
    token: str = _SYNTHETIC,
) -> Path:
    """Point the matcher at a temp data file built from ``token``."""
    path = policy_dir / "policy_terms.dat"
    hashes = sorted(candidate_hashes(token))
    path.write_text(
        "".join(f"{digest}\n" for digest in hashes),
        encoding="utf-8",
    )
    monkeypatch.setenv(policy_data.POLICY_DATA_ENV_VAR, str(path))
    policy_data.reset_cache()
    return path


# --------------------------------------------------------------------------
# Test doubles
# --------------------------------------------------------------------------


class _FakeApi:
    """Minimal app/api surface used by the route and worker tests."""

    def __init__(self) -> None:
        self.llm = None
        self.responses: list[tuple[object, object]] = []

    def emit_signal(self, _code, _data=None) -> None:
        """Ignore signal emissions during gate tests."""

    def worker_response(self, code, message) -> None:
        """Record one worker response."""
        self.responses.append((code, message))


def _route_client() -> TestClient:
    """Return a TestClient bound to a fresh FastAPI app."""
    os.environ["AIRUNNER_INSECURE_NO_AUTH"] = "1"
    app = create_app(
        allowed_origins=["http://localhost"],
        enable_cors=False,
        app_instance=_FakeApi(),
    )
    return TestClient(app)


def _patch_downstream(monkeypatch: pytest.MonkeyPatch, routes) -> None:
    """Replace the route's downstream work with inert fakes."""

    async def _noop(*_args, **_kwargs):
        return None

    class _FakeTracker:
        async def create_job(self, metadata=None):
            return "job-1"

        async def update_progress(self, *_args, **_kwargs):
            return None

    monkeypatch.setattr(routes, "unload_llm_before_art", _noop)
    monkeypatch.setattr(routes, "require_runtime_registry", lambda _req: object())
    monkeypatch.setattr(routes, "resolve_art_client", lambda _reg: object())
    monkeypatch.setattr(routes, "JobTracker", _FakeTracker)
    monkeypatch.setattr(routes, "run_art_job", _noop)


def _import_routes():
    return importlib.import_module(
        "airunner_services.api.routes.art_generation_start_routes"
    )


# --------------------------------------------------------------------------
# Shared gate helper
# --------------------------------------------------------------------------


def test_gate_message_is_generic_and_constant() -> None:
    assert gate.GENERIC_REJECTION_MESSAGE == (
        "Request rejected by content safety policy"
    )


def test_gate_reports_first_field_without_echoing_text(
    policy_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _load_synthetic_policy(policy_dir, monkeypatch)
    result = gate.evaluate_prompt_fields(
        {
            "prompt": f"please draw {_SYNTHETIC}",
            "negative_prompt": None,
        }
    )
    assert result.allowed is False
    assert result.field == "prompt"
    assert _SYNTHETIC not in result.reason
    assert _SYNTHETIC not in gate.GENERIC_REJECTION_MESSAGE


def test_gate_allows_unrelated_text(
    policy_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _load_synthetic_policy(policy_dir, monkeypatch)
    result = gate.evaluate_prompt_fields(
        {"prompt": "a calm neutral landscape", "negative_prompt": ""}
    )
    assert result.allowed is True
    assert result.field is None


# --------------------------------------------------------------------------
# HTTP route gate
# --------------------------------------------------------------------------


def test_route_rejects_matching_prompt_without_side_effects(
    policy_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    _load_synthetic_policy(policy_dir, monkeypatch)
    routes = _import_routes()
    unload_calls: list[bool] = []

    async def _spy_unload(*_args, **_kwargs):
        unload_calls.append(True)

    monkeypatch.setattr(routes, "unload_llm_before_art", _spy_unload)

    with caplog.at_level(logging.DEBUG):
        response = _route_client().post(
            _ART_ROUTE,
            json={"prompt": f"please draw {_SYNTHETIC}"},
        )

    assert response.status_code == 400
    body = response.json()
    assert body["detail"] == gate.GENERIC_REJECTION_MESSAGE
    assert _SYNTHETIC not in json.dumps(body)
    # The gate ran before the first side effect.
    assert unload_calls == []
    # No raw prompt text is logged on the rejection path.
    assert all(
        _SYNTHETIC not in record.getMessage() for record in caplog.records
    )


def test_route_allows_unrelated_prompt(
    policy_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _load_synthetic_policy(policy_dir, monkeypatch)
    routes = _import_routes()
    _patch_downstream(monkeypatch, routes)

    response = _route_client().post(
        _ART_ROUTE,
        json={"prompt": "a totally unrelated neutral prompt"},
    )

    assert response.status_code == 200
    assert response.json()["job_id"] == "job-1"
    assert response.json()["status"] == "running"


def test_route_allows_when_policy_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # No env override: the packaged policy set is empty, so checks pass.
    policy_data.reset_cache()
    routes = _import_routes()
    _patch_downstream(monkeypatch, routes)

    response = _route_client().post(
        _ART_ROUTE,
        json={"prompt": _SYNTHETIC},
    )

    assert response.status_code == 200
    assert response.json()["job_id"] == "job-1"


def test_legacy_art_route_rejects_matching_prompt(
    policy_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _load_synthetic_policy(policy_dir, monkeypatch)

    response = _route_client().post(
        "/art",
        json={"prompt": f"please draw {_SYNTHETIC}"},
    )

    assert response.status_code == 400
    body = response.json()
    assert body["detail"] == gate.GENERIC_REJECTION_MESSAGE
    assert _SYNTHETIC not in json.dumps(body)


# --------------------------------------------------------------------------
# SDWorker signal-boundary gate
# --------------------------------------------------------------------------


def _make_worker():
    from airunner_services.workers.sd_worker import SDWorker

    worker = object.__new__(SDWorker)
    worker.logger = logging.getLogger("content-safety-gate-test")
    worker.api = _FakeApi()
    worker.emit_signal = lambda *_args, **_kwargs: None
    errors: list[str] = []
    worker.handle_error = errors.append
    load_calls: list[dict] = []
    worker.load_model_manager = lambda data=None: load_calls.append(data)
    return worker, errors, load_calls


def test_worker_rejects_matching_request_before_model_load(
    policy_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    from airunner_services.art.managers.stablediffusion.image_request import (
        ImageRequest,
    )
    from airunner_common.contract_enums import EngineResponseCode

    _load_synthetic_policy(policy_dir, monkeypatch)
    worker, errors, load_calls = _make_worker()
    request = ImageRequest(prompt=f"draw {_SYNTHETIC}")

    with caplog.at_level(logging.DEBUG):
        worker._generate_image({"image_request": request})

    assert errors == [gate.GENERIC_REJECTION_MESSAGE]
    assert load_calls == []
    assert worker.api.responses[-1] == (
        EngineResponseCode.ERROR,
        gate.GENERIC_REJECTION_MESSAGE,
    )
    assert all(
        _SYNTHETIC not in record.getMessage() for record in caplog.records
    )


def test_worker_reports_generic_message_to_callback(
    policy_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from airunner_services.art.managers.stablediffusion.image_request import (
        ImageRequest,
    )

    _load_synthetic_policy(policy_dir, monkeypatch)
    worker, _errors, _load_calls = _make_worker()
    callbacks: list[str] = []
    request = ImageRequest(
        prompt=f"draw {_SYNTHETIC}",
        callback=callbacks.append,
    )

    worker._generate_image({"image_request": request})

    assert callbacks == [gate.GENERIC_REJECTION_MESSAGE]
    assert _SYNTHETIC not in callbacks[0]


def test_worker_allows_unrelated_request(
    policy_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from airunner_services.art.managers.stablediffusion.image_request import (
        ImageRequest,
    )

    _load_synthetic_policy(policy_dir, monkeypatch)
    worker, errors, load_calls = _make_worker()

    worker._generate_image(
        {"image_request": ImageRequest(prompt="a neutral scene")}
    )

    assert errors == []
    assert len(load_calls) == 1


def test_worker_allows_when_policy_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from airunner_services.art.managers.stablediffusion.image_request import (
        ImageRequest,
    )

    policy_data.reset_cache()
    worker, errors, load_calls = _make_worker()

    worker._generate_image({"image_request": ImageRequest(prompt=_SYNTHETIC)})

    assert errors == []
    assert len(load_calls) == 1


# --------------------------------------------------------------------------
# LLM image tool pre-check
# --------------------------------------------------------------------------


def _install_tool_doubles(monkeypatch: pytest.MonkeyPatch):
    image_tools = importlib.import_module(
        "airunner_services.llm.tools.image_tools"
    )
    caps = SimpleNamespace(
        dimension_step=64,
        min_width=64,
        max_width=2048,
        min_height=64,
        max_height=2048,
        supports_second_prompt=True,
        supports_negative_prompt=True,
    )
    monkeypatch.setattr(
        image_tools,
        "_get_current_generator_capabilities",
        lambda _api: (caps, "test-generator"),
    )
    enhance_calls: list[tuple[str, str]] = []

    def _fake_enhance(prompt: str, second_prompt: str = ""):
        enhance_calls.append((prompt, second_prompt))
        return prompt, second_prompt

    monkeypatch.setattr(
        image_tools,
        "enhance_prompt_with_specialized_model",
        _fake_enhance,
    )
    return image_tools, enhance_calls


class _FakeArt:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def llm_image_generated(self, **kwargs) -> None:
        self.calls.append(kwargs)


def test_tool_precheck_rejects_without_dispatch(
    policy_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _load_synthetic_policy(policy_dir, monkeypatch)
    image_tools, enhance_calls = _install_tool_doubles(monkeypatch)
    art = _FakeArt()

    result = image_tools.generate_image(
        prompt=f"draw {_SYNTHETIC}",
        api=SimpleNamespace(art=art),
    )

    payload = json.loads(result)
    assert payload["status"] == "rejected"
    assert payload["message"] == gate.GENERIC_REJECTION_MESSAGE
    assert _SYNTHETIC not in json.dumps(payload)
    # Neither enhancement nor dispatch happens on a rejected request.
    assert enhance_calls == []
    assert art.calls == []


def test_tool_precheck_allows_unrelated_prompt(
    policy_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _load_synthetic_policy(policy_dir, monkeypatch)
    image_tools, enhance_calls = _install_tool_doubles(monkeypatch)
    art = _FakeArt()

    result = image_tools.generate_image(
        prompt="a neutral scene",
        api=SimpleNamespace(art=art),
    )

    payload = json.loads(result)
    assert payload["status"] == "generating"
    assert enhance_calls and len(art.calls) == 1
