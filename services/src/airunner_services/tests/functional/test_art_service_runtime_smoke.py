"""Smoke tests for the direct art service runtime boundary."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


os.environ.setdefault("AIRUNNER_TEST_NO_GUI_LAUNCH", "1")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


_SERVICES_ROOT = Path(__file__).resolve().parents[3]
_PROJECT_ROOT = _SERVICES_ROOT.parent.parent.parent

for _path in (
    _PROJECT_ROOT / "services" / "src",
    _PROJECT_ROOT / "model" / "src",
    _PROJECT_ROOT / "native" / "src",
    _PROJECT_ROOT / "src",
):
    _path_str = str(_path)
    if _path_str not in sys.path:
        sys.path.append(_path_str)


from airunner_model.session import reset_engine
from airunner_model.models.application_settings import ApplicationSettings
from airunner_model.models.generator_settings import GeneratorSettings
from airunner_model.models.path_settings import PathSettings
from airunner_model.setup_database import setup_database
from airunner_services.app.service_app import ServiceApp
from airunner_services.contract_enums import Scheduler, StableDiffusionVersion
from airunner_services.runtimes.local_fallback import LocalFallbackArtClient


_PROBE_RESULT_PREFIX = "ART_RUNTIME_RESULT:"
pytestmark = [pytest.mark.art_service_runtime]


def _configure_test_database(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> str:
    db_url = f"sqlite:///{tmp_path / 'art-service-runtime.sqlite'}"
    monkeypatch.setenv("AIRUNNER_DATABASE_URL", db_url)
    monkeypatch.setenv("AIRUNNER_DISABLE_DB_SETUP_CACHE", "1")
    monkeypatch.setenv("AIRUNNER_KNOWLEDGE_ON", "0")
    monkeypatch.setenv("AIRUNNER_NO_PRELOAD", "1")
    monkeypatch.setenv("AIRUNNER_INSECURE_NO_AUTH", "1")
    monkeypatch.delenv("AIRUNNER_SERVER_RUNNING", raising=False)
    reset_engine()
    setup_database()
    return db_url


def _ensure_row(model_class, **defaults):
    instance = model_class.objects.first()
    if instance is None:
        instance = model_class.objects.create(**defaults)
    return instance or model_class.objects.first()


def _seed_art_runtime_settings(runtime_root: Path, output_root: Path) -> None:
    app_settings = _ensure_row(ApplicationSettings)
    ApplicationSettings.objects.update(
        pk=getattr(app_settings, "id", None),
        sd_enabled=True,
        llm_enabled=False,
        tts_enabled=False,
        stt_enabled=False,
        controlnet_enabled=False,
        nsfw_filter=False,
        auto_export_images=False,
        working_width=512,
        working_height=512,
    )

    path_settings = _ensure_row(PathSettings)
    PathSettings.objects.update(
        pk=getattr(path_settings, "id", None),
        base_path=str(runtime_root),
        image_path=str(output_root),
    )

    generator_settings = _ensure_row(GeneratorSettings)
    GeneratorSettings.objects.update(
        pk=getattr(generator_settings, "id", None),
        pipeline_action="txt2img",
        version=StableDiffusionVersion.SDXL1_0.value,
        scheduler=Scheduler.EULER.value,
        steps=4,
        scale=500,
        use_compel=True,
    )


def _art_models_root() -> Path:
    return Path.home() / ".local" / "share" / "airunner" / "art" / "models"


def _require_cuda() -> None:
    try:
        import torch
    except Exception as exc:
        pytest.skip(f"PyTorch unavailable: {exc}")

    try:
        if not torch.cuda.is_available():
            pytest.skip("CUDA is required for real art service tests")
    except Exception as exc:
        pytest.skip(f"CUDA check failed: {exc}")


def _require_model_file(version: str, pipeline_action: str) -> Path:
    action_dir = _art_models_root() / version / pipeline_action
    if not action_dir.is_dir():
        pytest.skip(f"Missing local art model directory: {action_dir}")

    for extension in ("*.safetensors", "*.ckpt", "*.gguf"):
        candidates = sorted(action_dir.glob(extension))
        if candidates:
            return candidates[0]

    pytest.skip(f"No model file found under {action_dir}")


def _probe_script_path() -> Path:
    return Path(__file__).with_name("art_service_runtime_probe.py")


def _run_runtime_probe(
    *,
    tmp_path: Path,
    model_path: Path,
    version: str,
    scheduler: str,
    prompt: str,
) -> dict[str, object]:
    db_url = f"sqlite:///{tmp_path / 'art-service-runtime-probe.sqlite'}"
    output_root = tmp_path / "probe-generated-images"
    output_root.mkdir(parents=True, exist_ok=True)

    env = os.environ.copy()
    env.update(
        {
            "AIRUNNER_DATABASE_URL": db_url,
            "AIRUNNER_DISABLE_DB_SETUP_CACHE": "1",
            "AIRUNNER_KNOWLEDGE_ON": "0",
            "AIRUNNER_NO_PRELOAD": "1",
            "AIRUNNER_INSECURE_NO_AUTH": "1",
            "PYTORCH_CUDA_ALLOC_CONF": "backend:cudaMallocAsync",
        }
    )
    env.pop("AIRUNNER_SERVER_RUNNING", None)

    completed = subprocess.run(
        [
            sys.executable,
            str(_probe_script_path()),
            "--model-path",
            str(model_path),
            "--version",
            version,
            "--scheduler",
            scheduler,
            "--prompt",
            prompt,
            "--runtime-root",
            str(Path.home() / ".local" / "share" / "airunner"),
            "--output-root",
            str(output_root),
        ],
        cwd=str(_PROJECT_ROOT),
        env=env,
        text=True,
        capture_output=True,
        timeout=1200,
    )

    result = None
    for line in reversed(completed.stdout.splitlines()):
        if line.startswith(_PROBE_RESULT_PREFIX):
            result = json.loads(line[len(_PROBE_RESULT_PREFIX) :])
            break

    if result is not None and result.get("status") == "skipped":
        pytest.skip(str(result.get("reason") or "runtime probe skipped"))

    if completed.returncode != 0:
        pytest.fail(
            "Runtime probe failed.\n"
            f"stdout:\n{completed.stdout}\n"
            f"stderr:\n{completed.stderr}"
        )

    if result is None:
        pytest.fail(
            "Runtime probe produced no result payload.\n"
            f"stdout:\n{completed.stdout}\n"
            f"stderr:\n{completed.stderr}"
        )

    return result


def _stop_worker(worker) -> None:
    if worker is None:
        return

    stop = getattr(worker, "stop", None)
    if callable(stop):
        stop()

    thread_getter = getattr(worker, "thread", None)
    if not callable(thread_getter):
        return

    thread = thread_getter()
    if thread is None:
        return

    quit_thread = getattr(thread, "quit", None)
    if callable(quit_thread):
        quit_thread()

    wait = getattr(thread, "wait", None)
    if callable(wait):
        wait(5000)


def _cleanup_service_app(app: ServiceApp) -> None:
    from airunner_services.api.legacy_server import set_api

    worker_manager = getattr(app, "_worker_manager", None)
    if worker_manager is not None:
        _stop_worker(getattr(worker_manager, "_sd_worker", None))
        _stop_worker(getattr(worker_manager, "_image_export_worker", None))
        _stop_worker(getattr(worker_manager, "_llm_generate_worker", None))

    cleanup = getattr(app, "cleanup", None)
    if callable(cleanup):
        cleanup()

    set_api(None)
    reset_engine()


@pytest.fixture
def service_app(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> ServiceApp:
    _configure_test_database(monkeypatch, tmp_path)
    _seed_art_runtime_settings(
        runtime_root=Path.home() / ".local" / "share" / "airunner",
        output_root=tmp_path / "generated-images",
    )
    app = ServiceApp(
        start_headless_api_server=False,
        initialize_headless_lifecycle=True,
    )
    try:
        yield app
    finally:
        _cleanup_service_app(app)


@pytest.mark.art_runtime_smoke
@pytest.mark.integration
def test_direct_art_runtime_bootstraps_headless_worker_only(
    service_app: ServiceApp,
) -> None:
    """The direct art runtime can create the SD worker without HTTP."""
    client = LocalFallbackArtClient(signal_source=service_app)

    assert service_app.api_server_thread is None
    assert service_app._worker_manager is not None

    worker = client._headless_art_worker(create=True)

    assert worker is not None
    assert worker is service_app._worker_manager.sd_worker
    assert client._art_model_manager(create=False) is worker.model_manager


@pytest.mark.gpu
@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.timeout(600)
def test_sdxl_txt2img_generates_image_through_direct_service_runtime(
    tmp_path: Path,
) -> None:
    """SDXL txt2img succeeds through the direct service runtime boundary."""
    model_path = _require_model_file(
        StableDiffusionVersion.SDXL1_0.value,
        "txt2img",
    )
    result = _run_runtime_probe(
        tmp_path=tmp_path,
        model_path=model_path,
        version=StableDiffusionVersion.SDXL1_0.value,
        scheduler=Scheduler.EULER.value,
        prompt="A product photo of a red ceramic mug on a plain table.",
    )

    assert result["status"] == "succeeded"
    assert result["response_status"] == "succeeded"
    assert result["image_count"] == 1
    assert result["image_size"] == [512, 512]
    assert result["progress_count"] >= 1


@pytest.mark.gpu
@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.timeout(600)
def test_zimage_txt2img_generates_image_through_direct_service_runtime(
    tmp_path: Path,
) -> None:
    """Z-Image txt2img succeeds through the direct service runtime boundary."""
    model_path = _require_model_file(
        StableDiffusionVersion.Z_IMAGE_TURBO.value,
        "txt2img",
    )
    result = _run_runtime_probe(
        tmp_path=tmp_path,
        model_path=model_path,
        version=StableDiffusionVersion.Z_IMAGE_TURBO.value,
        scheduler=Scheduler.FLOW_MATCH_EULER.value,
        prompt="A cinematic portrait of a fox in a rainy neon alley.",
    )

    assert result["status"] == "succeeded"
    assert result["response_status"] == "succeeded"
    assert result["image_count"] == 1
    assert result["image_size"] == [512, 512]
    assert result["progress_count"] >= 1
