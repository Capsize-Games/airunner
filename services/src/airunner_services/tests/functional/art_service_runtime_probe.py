"""Run one direct art service runtime probe in a fresh interpreter."""

from __future__ import annotations

import argparse
import base64
import io
import json
import os
import sys
from pathlib import Path

from PIL import Image


os.environ.setdefault("AIRUNNER_TEST_NO_GUI_LAUNCH", "1")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("AIRUNNER_KNOWLEDGE_ON", "0")
os.environ.setdefault("AIRUNNER_NO_PRELOAD", "1")
os.environ.setdefault("AIRUNNER_INSECURE_NO_AUTH", "1")
os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "backend:cudaMallocAsync")


RESULT_PREFIX = "ART_RUNTIME_RESULT:"
HERE = Path(__file__).resolve()
PROJECT_ROOT = HERE.parents[5]

for path in (
    PROJECT_ROOT / "services" / "src",
    PROJECT_ROOT / "model" / "src",
    PROJECT_ROOT / "native" / "src",
    PROJECT_ROOT / "src",
):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.append(path_str)


from airunner_model.models.application_settings import ApplicationSettings
from airunner_model.models.generator_settings import GeneratorSettings
from airunner_model.models.path_settings import PathSettings
from airunner_services.art.managers.zimage.zimage_bundle_requirements import (
    get_active_zimage_load_mode,
    get_missing_files_for_mode,
)
from airunner_model.session import reset_engine
from airunner_services.app.service_app import ServiceApp
from airunner_services.ipc.messages import EnvelopeStatus, RequestEnvelope
from airunner_services.runtimes.contracts import (
    ArtInvocationRequest,
    RuntimeAction,
    RuntimeKind,
)
from airunner_services.runtimes.local_fallback import LocalFallbackArtClient
from airunner_services.setup_database import setup_database


def _emit_result(status: str, **payload: object) -> None:
    data = {"status": status, **payload}
    print(f"{RESULT_PREFIX}{json.dumps(data)}", flush=True)


def _ensure_row(model_class, **defaults):
    instance = model_class.objects.first()
    if instance is None:
        instance = model_class.objects.create(**defaults)
    return instance or model_class.objects.first()


def _seed_art_runtime_settings(
    *,
    runtime_root: Path,
    output_root: Path,
    version: str,
    scheduler: str,
) -> None:
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
        version=version,
        scheduler=scheduler,
        steps=4,
        scale=500,
        use_compel=True,
    )


def _build_request(
    *,
    model_path: Path,
    version: str,
    scheduler: str,
    prompt: str,
) -> RequestEnvelope:
    payload = ArtInvocationRequest(
        prompt=prompt,
        negative_prompt="",
        model=str(model_path),
        width=512,
        height=512,
        steps=4,
        cfg_scale=5.0,
        seed=1234,
        num_images=1,
        metadata={
            "version": version,
            "pipeline": "txt2img",
            "scheduler": scheduler,
            "skip_auto_export": True,
        },
    ).model_dump()
    return RequestEnvelope(
        runtime=RuntimeKind.ART,
        action=RuntimeAction.INVOKE,
        provider="local",
        payload=payload,
    )


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


def _cleanup_service_app(app: ServiceApp | None) -> None:
    if app is None:
        return
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


def _cuda_ready() -> tuple[bool, str]:
    try:
        import torch
    except Exception as exc:
        return False, f"PyTorch unavailable: {exc}"

    try:
        if not torch.cuda.is_available():
            return False, "CUDA is required for real art service tests"
    except Exception as exc:
        return False, f"CUDA check failed: {exc}"

    return True, ""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-path", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--scheduler", required=True)
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--runtime-root", required=True)
    parser.add_argument("--output-root", required=True)
    args = parser.parse_args()

    cuda_ready, reason = _cuda_ready()
    if not cuda_ready:
        _emit_result("skipped", reason=reason)
        return 0

    model_path = Path(args.model_path)
    if not model_path.exists():
        _emit_result("failed", reason=f"Missing model path: {model_path}")
        return 1

    if args.version == "Z-Image Turbo":
        load_mode = get_active_zimage_load_mode(model_path)
        missing_files = get_missing_files_for_mode(model_path, load_mode)
        if missing_files:
            _emit_result(
                "skipped",
                reason=(
                    "Z-Image bundle missing required files for "
                    f"{load_mode}: {', '.join(missing_files)}"
                ),
            )
            return 0

    output_root = Path(args.output_root)
    output_root.mkdir(parents=True, exist_ok=True)

    reset_engine()
    setup_database()
    _seed_art_runtime_settings(
        runtime_root=Path(args.runtime_root),
        output_root=output_root,
        version=args.version,
        scheduler=args.scheduler,
    )

    app = None
    try:
        app = ServiceApp(
            start_headless_api_server=False,
            initialize_headless_lifecycle=True,
        )
        client = LocalFallbackArtClient(signal_source=app)
        progress_updates = []
        response = client.invoke_with_progress(
            _build_request(
                model_path=model_path,
                version=args.version,
                scheduler=args.scheduler,
                prompt=args.prompt,
            ),
            progress_updates.append,
        )
        if response.status is not EnvelopeStatus.SUCCEEDED:
            _emit_result(
                "failed",
                reason="Art invocation did not succeed",
                response_status=response.status.value,
            )
            return 1

        images = response.payload.get("images") or []
        if not images:
            _emit_result(
                "failed",
                reason="Art invocation returned no images",
                response_status=response.status.value,
            )
            return 1

        with Image.open(io.BytesIO(base64.b64decode(images[0]))) as image:
            _emit_result(
                "succeeded",
                response_status=response.status.value,
                image_count=len(images),
                image_size=list(image.size),
                progress_count=len(progress_updates),
            )
        return 0
    except Exception as exc:
        _emit_result("failed", reason=str(exc))
        return 1
    finally:
        _cleanup_service_app(app)


if __name__ == "__main__":
    raise SystemExit(main())