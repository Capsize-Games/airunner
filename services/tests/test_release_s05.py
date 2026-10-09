"""Release regression tests for issue #2100 (S05).

Image generation must be denied -- before jobs, model loads, or prompt
enhancement -- when mandatory content-safety policy data is missing,
empty, or invalid. A valid neutral policy still allows safe fixtures and
rejects matching ones, and non-generation app use still works.

Every token used here is synthetic and neutral. No real policy term
appears in this file, and no assertion inspects a log record or response
body beyond checking that the synthetic input text is absent.
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
from airunner_services.content_safety import (
    check_text,
    hash_token,
    is_available,
    policy_data,
)
from airunner_services.content_safety.matcher import (
    REASON_POLICY_UNAVAILABLE,
    REASON_PROHIBITED,
)

_REPO_ROOT = Path(__file__).resolve().parents[2]
_ART_ROUTE = "/api/v1/art/generate"

_SYNTHETIC = "quibblesprocket"
_SAFE = "a calm neutral landscape"


@pytest.fixture
def policy_dir() -> Iterator[Path]:
    """Create a scratch dir under the (gitignored) repo-local tmp/ tree."""
    base = _REPO_ROOT / "tmp" / "content_safety_tests"
    base.mkdir(parents=True, exist_ok=True)
    created = Path(tempfile.mkdtemp(prefix="s05_", dir=base))
    yield created
    shutil.rmtree(created, ignore_errors=True)


@pytest.fixture(autouse=True)
def _clean_policy_cache(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.delenv(policy_data.POLICY_DATA_ENV_VAR, raising=False)
    policy_data.reset_cache()
    yield
    policy_data.reset_cache()


def _load(path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(policy_data.POLICY_DATA_ENV_VAR, str(path))
    policy_data.reset_cache()


def _load_valid_policy(
    policy_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Point the matcher at a valid neutral single-hash policy file."""
    path = policy_dir / "policy_terms.dat"
    path.write_text(hash_token(_SYNTHETIC) + "\n", encoding="utf-8")
    _load(path, monkeypatch)


def _load_invalid_policy(
    policy_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Point the matcher at a versioned artifact with a bad digest."""
    path = policy_dir / "policy_terms.dat"
    path.write_text(
        "# format: airunner-policy-data/1\n"
        "# normalization: v1\n"
        "# count: 1\n"
        "# sha256: " + "0" * 64 + "\n" + hash_token(_SYNTHETIC) + "\n",
        encoding="utf-8",
    )
    _load(path, monkeypatch)


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


def _import_routes():
    return importlib.import_module(
        "airunner_services.api.routes.art_generation_start_routes"
    )


def _make_worker():
    from airunner_services.workers.sd_worker import SDWorker

    worker = object.__new__(SDWorker)
    worker.logger = logging.getLogger("release-s05-test")
    worker.api = _FakeApi()
    worker.emit_signal = lambda *_args, **_kwargs: None
    errors: list[str] = []
    worker.handle_error = errors.append
    load_calls: list[dict] = []
    worker.load_model_manager = lambda data=None: load_calls.append(data)
    return worker, errors, load_calls


# --------------------------------------------------------------------------
# Unavailable policy denies generation before side effects
# --------------------------------------------------------------------------


def test_missing_policy_denies_route_before_job(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    policy_data.reset_cache()
    assert is_available() is False
    routes = _import_routes()
    unload_calls: list[bool] = []

    async def _spy_unload(*_args, **_kwargs):
        unload_calls.append(True)

    monkeypatch.setattr(routes, "unload_llm_before_art", _spy_unload)
    with caplog.at_level(logging.DEBUG):
        response = _route_client().post(
            _ART_ROUTE, json={"prompt": f"draw {_SYNTHETIC}"}
        )
    assert response.status_code == 400
    body = response.json()
    assert body["detail"] == gate.GENERIC_POLICY_ERROR_MESSAGE
    assert _SYNTHETIC not in json.dumps(body)
    assert unload_calls == []
    assert all(
        _SYNTHETIC not in record.getMessage() for record in caplog.records
    )


def test_empty_policy_denies_worker_before_model_load(
    policy_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from airunner_services.art.managers.stablediffusion.image_request import (
        ImageRequest,
    )

    path = policy_dir / "empty.dat"
    path.write_text("", encoding="utf-8")
    _load(path, monkeypatch)
    assert is_available() is False
    worker, errors, load_calls = _make_worker()
    worker._generate_image({"image_request": ImageRequest(prompt=_SAFE)})
    assert errors == [gate.GENERIC_POLICY_ERROR_MESSAGE]
    assert load_calls == []


def test_invalid_policy_denies_gate_with_policy_reason(
    policy_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _load_invalid_policy(policy_dir, monkeypatch)
    assert is_available() is False
    assert check_text(_SAFE) is False
    result = gate.evaluate_prompt_fields({"prompt": _SAFE})
    assert result.allowed is False
    assert result.reason == REASON_POLICY_UNAVAILABLE
    assert result.field is None
    assert gate.rejection_message(result) == (
        gate.GENERIC_POLICY_ERROR_MESSAGE
    )


def test_tool_precheck_denies_without_dispatch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
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
        image_tools, "enhance_prompt_with_specialized_model", _fake_enhance
    )
    dispatches: list[dict] = []

    class _FakeArt:
        def llm_image_generated(self, **kwargs) -> None:
            dispatches.append(kwargs)

    policy_data.reset_cache()
    payload = json.loads(
        image_tools.generate_image(
            prompt=_SAFE, api=SimpleNamespace(art=_FakeArt())
        )
    )
    assert payload["status"] == "rejected"
    assert _SAFE not in json.dumps(payload)
    assert enhance_calls == []
    assert dispatches == []


# --------------------------------------------------------------------------
# Valid neutral policy still gates on content
# --------------------------------------------------------------------------


def test_valid_policy_allows_safe_and_rejects_matching(
    policy_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _load_valid_policy(policy_dir, monkeypatch)
    assert is_available() is True
    assert gate.evaluate_prompt_fields({"prompt": _SAFE}).allowed is True
    result = gate.evaluate_prompt_fields(
        {"prompt": f"please draw {_SYNTHETIC}"}
    )
    assert result.allowed is False
    assert result.reason == REASON_PROHIBITED
    assert result.field == "prompt"
    assert gate.rejection_message(result) == (gate.GENERIC_REJECTION_MESSAGE)


def test_valid_policy_route_allows_safe_prompt(
    policy_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _load_valid_policy(policy_dir, monkeypatch)
    routes = _import_routes()

    async def _noop(*_args, **_kwargs):
        return None

    class _FakeTracker:
        async def create_job(self, metadata=None):
            return "job-1"

        async def update_progress(self, *_args, **_kwargs):
            return None

    monkeypatch.setattr(routes, "unload_llm_before_art", _noop)
    monkeypatch.setattr(
        routes, "require_runtime_registry", lambda _req: object()
    )
    monkeypatch.setattr(routes, "resolve_art_client", lambda _reg: object())
    monkeypatch.setattr(routes, "JobTracker", _FakeTracker)
    monkeypatch.setattr(routes, "run_art_job", _noop)
    response = _route_client().post(_ART_ROUTE, json={"prompt": _SAFE})
    assert response.status_code == 200
    assert response.json()["job_id"] == "job-1"


# --------------------------------------------------------------------------
# Non-generation app use still works without policy data
# --------------------------------------------------------------------------


def test_non_generation_use_without_policy_data() -> None:
    policy_data.reset_cache()
    assert is_available() is False
    assert check_text("") is True
    os.environ["AIRUNNER_INSECURE_NO_AUTH"] = "1"
    app = create_app(allowed_origins=["http://localhost"], enable_cors=True)
    response = TestClient(app).get("/")
    assert response.status_code == 200
