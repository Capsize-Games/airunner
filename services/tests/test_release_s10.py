"""Release regression tests for issue #2109 (S10).

Mandatory input-image screening on final resolved img2img/inpaint/
outpaint/reference-image requests before model dispatch, on both the
API route path and the signal-driven worker path. A blocked or
unavailable verdict prevents inference; decoding and screening never
preview or export the inputs.

Every image here is a tiny synthetic solid-colour PIL image created
in-process (base64-encoded only to cross the request contract), and
every evaluator is a synthetic double. No real imagery, prompt, or
policy term is used. No model is loaded and no network is used.
"""

from __future__ import annotations

import base64
import importlib
import io
import json
import os
import shutil
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from airunner_services import content_safety_gate as gate
from airunner_services.api.server import create_app
from airunner_services.api.routes import art_contracts
from airunner_services.api.routes.art_contracts import GenerationRequest
from airunner_services.content_safety import (
    hash_token,
    is_available,
    policy_data,
)
from airunner_services.content_safety import image_verdict

_REPO_ROOT = Path(__file__).resolve().parents[2]
_ART_ROUTE = "/api/v1/art/generate"

_SYNTHETIC = "zibberflaston"
_SAFE = "a calm neutral landscape"
_ORIGINAL_COLOR = (40, 120, 200)


@pytest.fixture
def policy_dir() -> Iterator[Path]:
    """Create a scratch dir under the (gitignored) repo-local tmp/ tree."""
    base = _REPO_ROOT / "tmp" / "content_safety_tests"
    base.mkdir(parents=True, exist_ok=True)
    created = Path(tempfile.mkdtemp(prefix="s10_", dir=base))
    yield created
    shutil.rmtree(created, ignore_errors=True)


@pytest.fixture(autouse=True)
def _clean_state(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.delenv(policy_data.POLICY_DATA_ENV_VAR, raising=False)
    policy_data.reset_cache()
    image_verdict.set_evaluator(None)
    yield
    policy_data.reset_cache()
    image_verdict.set_evaluator(None)


def _load_valid_policy(
    policy_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Point the matcher at a valid neutral single-hash policy file."""
    path = policy_dir / "policy_terms.dat"
    path.write_text(hash_token(_SYNTHETIC) + "\n", encoding="utf-8")
    monkeypatch.setenv(policy_data.POLICY_DATA_ENV_VAR, str(path))
    policy_data.reset_cache()


def _synthetic_image(color=_ORIGINAL_COLOR) -> Image.Image:
    """Return a tiny solid-colour in-memory image (never saved)."""
    return Image.new("RGB", (8, 8), color)


def _synthetic_image_b64() -> str:
    """Return one synthetic PNG payload for the request contract."""
    buffer = io.BytesIO()
    _synthetic_image().save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("ascii")


def _is_original(image: Image.Image) -> bool:
    """True when the image still holds the untouched fixture colour."""
    return image.convert("RGB").getpixel((0, 0)) == _ORIGINAL_COLOR


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
    worker.logger = _StubLogger()
    worker.api = _FakeApi()
    worker.emit_signal = lambda *_args, **_kwargs: None
    errors: list[str] = []
    worker.handle_error = errors.append
    load_calls: list[dict] = []
    worker.load_model_manager = lambda data=None: load_calls.append(data)
    return worker, errors, load_calls


class _StubLogger:
    """Recording stand-in for the production logger wrapper.

    The production ``Logger`` wrapper sets ``propagate = False``, so
    handler attachment and caplog cannot observe its records. Both
    call sites only use ``info``/``warning`` with printf-style args.
    """

    def __init__(self) -> None:
        self.messages: list[str] = []

    def _record(self, message: str, *args) -> None:
        if args:
            message = message % args
        self.messages.append(message)

    def debug(self, message: str, *args, **_kwargs) -> None:
        """Record one debug message."""
        self._record(message, *args)

    def info(self, message: str, *args, **_kwargs) -> None:
        """Record one info message."""
        self._record(message, *args)

    def warning(self, message: str, *args, **_kwargs) -> None:
        """Record one warning message."""
        self._record(message, *args)

    def error(self, message: str, *args, **_kwargs) -> None:
        """Record one error message."""
        self._record(message, *args)


@contextmanager
def _capture_route_logs(routes, monkeypatch: pytest.MonkeyPatch):
    """Record messages logged by the route module during one block."""
    stub = _StubLogger()
    monkeypatch.setattr(routes, "logger", stub)
    yield stub


def _allow_all(images):
    return [False] * len(list(images))


def _flag_all(images):
    return [True] * len(list(images))


def _stub_route_runtime(
    routes, monkeypatch: pytest.MonkeyPatch, tracker_spy: list
) -> list:
    """Replace route side effects with spies; return unload calls."""
    unload_calls: list[bool] = []

    async def _spy_unload(*_args, **_kwargs):
        unload_calls.append(True)

    async def _noop(*_args, **kwargs):
        return None

    class _FakeTracker:
        def __init__(self) -> None:
            tracker_spy.append(True)

        async def create_job(self, metadata=None):
            return "job-1"

        async def update_progress(self, *_args, **_kwargs):
            return None

    monkeypatch.setattr(routes, "unload_llm_before_art", _spy_unload)
    monkeypatch.setattr(
        routes, "require_runtime_registry", lambda _req: object()
    )
    monkeypatch.setattr(routes, "resolve_art_client", lambda _reg: object())
    monkeypatch.setattr(routes, "JobTracker", _FakeTracker)
    monkeypatch.setattr(routes, "run_art_job", _noop)
    return unload_calls


# --------------------------------------------------------------------------
# Shared decode helper: size/type validation without side effects
# --------------------------------------------------------------------------


def test_decode_accepts_real_image_within_bound() -> None:
    image = art_contracts.decode_input_image(_synthetic_image_b64())
    assert image.size == (8, 8)
    assert _is_original(image)


def test_decode_rejects_non_image_bytes() -> None:
    payload = base64.b64encode(b"0" * 64).decode("ascii")
    # The contract still passes within-bound opaque bytes (D04); the
    # input-image screen rejects them as undecodable images instead.
    GenerationRequest(prompt=_SAFE, image_b64=payload)
    with pytest.raises(ValueError, match="does not decode"):
        art_contracts.decode_input_image(payload)


def test_decode_rejects_invalid_base64() -> None:
    with pytest.raises(ValueError, match="not valid base64"):
        art_contracts.decode_input_image("not-valid-base64!!!")


def test_decode_enforces_size_bound(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("AIRUNNER_ART_MAX_IMAGE_BYTES", "10")
    monkeypatch.chdir(tmp_path)
    with pytest.raises(ValueError, match="exceeds the maximum"):
        art_contracts.decode_input_image(_synthetic_image_b64())
    assert list(tmp_path.iterdir()) == []


def test_decode_writes_no_files(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    art_contracts.decode_input_image(_synthetic_image_b64())
    assert list(tmp_path.iterdir()) == []


# --------------------------------------------------------------------------
# API path: route-level input-image screen
# --------------------------------------------------------------------------


def test_route_allows_image_bearing_request_when_allowed(
    policy_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _load_valid_policy(policy_dir, monkeypatch)
    assert is_available() is True
    image_verdict.set_evaluator(_allow_all)
    routes = _import_routes()
    tracker_spy: list[bool] = []
    unload_calls = _stub_route_runtime(routes, monkeypatch, tracker_spy)
    with _capture_route_logs(routes, monkeypatch) as logs:
        response = _route_client().post(
            _ART_ROUTE,
            json={"prompt": _SAFE, "image_b64": _synthetic_image_b64()},
        )
    assert response.status_code == 200
    assert response.json()["job_id"] == "job-1"
    assert unload_calls != []
    assert any(
        "path=api" in message and "image_gate=pass" in message
        for message in logs.messages
    )


def test_route_rejects_image_bearing_request_when_flagged(
    policy_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _load_valid_policy(policy_dir, monkeypatch)
    image_verdict.set_evaluator(_flag_all)
    routes = _import_routes()
    tracker_spy: list[bool] = []
    unload_calls = _stub_route_runtime(routes, monkeypatch, tracker_spy)
    with _capture_route_logs(routes, monkeypatch) as logs:
        response = _route_client().post(
            _ART_ROUTE,
            json={"prompt": _SAFE, "image_b64": _synthetic_image_b64()},
        )
    assert response.status_code == 400
    body = response.json()
    assert body["detail"] == gate.GENERIC_REJECTION_MESSAGE
    assert _SAFE not in json.dumps(body)
    assert "image_flagged" not in json.dumps(body)
    assert unload_calls == []
    assert tracker_spy == []
    assert any("input-image screen" in m for m in logs.messages)


def test_route_rejects_image_bearing_request_when_unavailable(
    policy_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _load_valid_policy(policy_dir, monkeypatch)
    assert image_verdict.get_evaluator() is None
    routes = _import_routes()
    tracker_spy: list[bool] = []
    unload_calls = _stub_route_runtime(routes, monkeypatch, tracker_spy)
    response = _route_client().post(
        _ART_ROUTE,
        json={"prompt": _SAFE, "image_b64": _synthetic_image_b64()},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == (gate.GENERIC_REJECTION_MESSAGE)
    assert unload_calls == []
    assert tracker_spy == []


def test_route_rejects_undecodable_image_before_side_effects(
    policy_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _load_valid_policy(policy_dir, monkeypatch)
    image_verdict.set_evaluator(_allow_all)
    routes = _import_routes()
    tracker_spy: list[bool] = []
    unload_calls = _stub_route_runtime(routes, monkeypatch, tracker_spy)
    opaque = base64.b64encode(b"0" * 64).decode("ascii")
    response = _route_client().post(
        _ART_ROUTE, json={"prompt": _SAFE, "image_b64": opaque}
    )
    assert response.status_code == 400
    assert "does not decode" in response.json()["detail"]
    assert unload_calls == []
    assert tracker_spy == []


def test_route_traces_text_only_request_as_no_image_coverage(
    policy_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _load_valid_policy(policy_dir, monkeypatch)
    image_verdict.set_evaluator(_flag_all)
    routes = _import_routes()
    tracker_spy: list[bool] = []
    _stub_route_runtime(routes, monkeypatch, tracker_spy)
    with _capture_route_logs(routes, monkeypatch) as logs:
        response = _route_client().post(_ART_ROUTE, json={"prompt": _SAFE})
    assert response.status_code == 200
    assert any("image_gate=skipped_no_inputs" in m for m in logs.messages)
    assert all("image_gate=pass" not in m for m in logs.messages)


# --------------------------------------------------------------------------
# Signal path: worker-level screen on final resolved requests
# --------------------------------------------------------------------------


def test_worker_screens_resolved_image_before_dispatch(
    policy_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from airunner_services.art.managers.stablediffusion.image_request import (
        ImageRequest,
    )

    _load_valid_policy(policy_dir, monkeypatch)
    image_verdict.set_evaluator(_allow_all)
    worker, errors, load_calls = _make_worker()
    image = _synthetic_image()
    worker._generate_image(
        {"image_request": ImageRequest(prompt=_SAFE, image=image)}
    )
    logs = worker.logger
    assert errors == []
    assert len(load_calls) == 1
    assert _is_original(image)
    assert any(
        "path=signal" in message and "image_gate=pass" in message
        for message in logs.messages
    )


@pytest.mark.parametrize("slot", ["image", "mask", "controlnet_image"])
def test_worker_blocks_each_image_slot_when_flagged(
    policy_dir: Path, monkeypatch: pytest.MonkeyPatch, slot: str
) -> None:
    from airunner_common.contract_enums import EngineResponseCode
    from airunner_services.art.managers.stablediffusion.image_request import (
        ImageRequest,
    )

    _load_valid_policy(policy_dir, monkeypatch)
    image_verdict.set_evaluator(_flag_all)
    worker, errors, load_calls = _make_worker()
    image = _synthetic_image()
    worker._generate_image(
        {"image_request": ImageRequest(prompt=_SAFE, **{slot: image})}
    )
    assert errors == [gate.GENERIC_REJECTION_MESSAGE]
    assert load_calls == []
    assert worker.api.responses[-1] == (
        EngineResponseCode.ERROR,
        gate.GENERIC_REJECTION_MESSAGE,
    )
    assert _is_original(image)


def test_worker_blocks_image_when_unavailable(
    policy_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from airunner_services.art.managers.stablediffusion.image_request import (
        ImageRequest,
    )

    _load_valid_policy(policy_dir, monkeypatch)
    assert image_verdict.get_evaluator() is None
    worker, errors, load_calls = _make_worker()
    worker._generate_image(
        {"image_request": ImageRequest(prompt=_SAFE, image=_synthetic_image())}
    )
    logs = worker.logger
    assert errors == [gate.GENERIC_REJECTION_MESSAGE]
    assert load_calls == []
    assert any("image_unavailable" in m for m in logs.messages)


def test_worker_traces_text_only_request_as_no_image_coverage(
    policy_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from airunner_services.art.managers.stablediffusion.image_request import (
        ImageRequest,
    )

    _load_valid_policy(policy_dir, monkeypatch)
    image_verdict.set_evaluator(_flag_all)
    worker, errors, load_calls = _make_worker()
    worker._generate_image({"image_request": ImageRequest(prompt=_SAFE)})
    logs = worker.logger
    assert errors == []
    assert len(load_calls) == 1
    assert any("image_gate=skipped_no_inputs" in m for m in logs.messages)
    assert all("image_gate=pass" not in m for m in logs.messages)


def test_worker_text_gate_runs_before_image_screen(
    policy_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from airunner_services.art.managers.stablediffusion.image_request import (
        ImageRequest,
    )

    _load_valid_policy(policy_dir, monkeypatch)
    image_verdict.set_evaluator(_allow_all)
    worker, errors, load_calls = _make_worker()
    worker._generate_image(
        {
            "image_request": ImageRequest(
                prompt=f"draw {_SYNTHETIC}",
                image=_synthetic_image(),
            )
        }
    )
    logs = worker.logger
    assert errors == [gate.GENERIC_REJECTION_MESSAGE]
    assert load_calls == []
    assert all("image_gate" not in m for m in logs.messages)
