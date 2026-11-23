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


from airunner_services.database.models.application_settings import ApplicationSettings
from airunner_services.database.models.generator_settings import GeneratorSettings
from airunner_services.database.models.path_settings import PathSettings
from airunner_services.database.setup_database import setup_database
from airunner_services.art.managers.zimage.zimage_bundle_requirements import (
    get_active_zimage_load_mode,
    get_missing_files_for_mode,
)
from airunner_services.database.session import reset_engine
from airunner_services.app.service_app import ServiceApp
from airunner_services.ipc.messages import EnvelopeStatus, RequestEnvelope
from airunner_services.model_management.zimage_model_manager import (
    ZImageModelManager,
)
from airunner_services.runtimes.contracts import (
    ArtInvocationRequest,
    RuntimeAction,
    RuntimeKind,
)
from airunner_services.runtimes.local_fallback import LocalFallbackArtClient


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
    pipeline_action: str,
    width: int = 512,
    height: int = 512,
    steps: int = 4,
    dtype: str = "bfloat16",
) -> None:
    app_settings = _ensure_row(ApplicationSettings)
    ApplicationSettings.objects.update(
        pk=getattr(app_settings, "id", None),
        sd_enabled=True,
        llm_enabled=False,
        tts_enabled=False,
        stt_enabled=False,
        nsfw_filter=False,
        auto_export_images=False,
        working_width=width,
        working_height=height,
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
        pipeline_action=pipeline_action,
        version=version,
        scheduler=scheduler,
        steps=steps,
        scale=500,
        use_compel=True,
        dtype=dtype,
    )


def _encode_image_file(image_path: Path) -> str:
    """Return one PNG base64 payload for a local image file."""
    with Image.open(image_path) as image:
        buffer = io.BytesIO()
        image.convert("RGB").save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("ascii")


def _zimage_supported_pipeline_actions() -> list[str]:
    """Return the Z-Image actions exposed by the service manager."""
    manager = object.__new__(ZImageModelManager)
    return sorted(manager.pipeline_map.keys())


def _build_request(
    *,
    model_path: Path,
    version: str,
    scheduler: str,
    prompt: str,
    pipeline_action: str,
    image_path: Path | None,
    mask_path: Path | None,
    strength: float | None,
    active_rect: dict[str, int] | None,
    width: int = 512,
    height: int = 512,
    steps: int = 4,
    seed: int = 1234,
    guidance: float = 5.0,
) -> RequestEnvelope:
    metadata = {
        "version": version,
        "pipeline": pipeline_action,
        "scheduler": scheduler,
        "skip_auto_export": True,
    }
    if strength is not None:
        metadata["strength"] = strength
    if image_path is not None:
        metadata["image_b64"] = _encode_image_file(image_path)
    if mask_path is not None:
        metadata["mask_b64"] = _encode_image_file(mask_path)
    if active_rect is not None:
        metadata["active_rect"] = active_rect

    payload = ArtInvocationRequest(
        prompt=prompt,
        negative_prompt="",
        model=str(model_path),
        width=width,
        height=height,
        steps=steps,
        cfg_scale=guidance,
        seed=seed,
        num_images=1,
        metadata=metadata,
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
    from airunner_services.api.runtime import set_api

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


def _batch_jobs(args) -> list[dict]:
    """One job per batch entry, or the single CLI request as a job."""
    if args.batch:
        jobs = []
        for i, entry in enumerate(json.loads(Path(args.batch).read_text())):
            jobs.append({
                "prompt": entry["prompt"],
                "seed": int(entry.get("seed", args.seed)),
                "width": int(entry.get("width", args.width)),
                "height": int(entry.get("height", args.height)),
                "steps": int(entry.get("steps", args.steps)),
                "guidance": float(entry.get("guidance", args.guidance)),
                "out": str(entry.get("out", f"probe_image_{i}.png")),
            })
        return jobs
    return [{
        "prompt": args.prompt,
        "seed": args.seed,
        "width": args.width,
        "height": args.height,
        "steps": args.steps,
        "guidance": args.guidance,
        "out": "probe_image.png",
    }]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-path", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--scheduler", required=True)
    parser.add_argument("--pipeline-action", default="txt2img")
    parser.add_argument("--prompt", default="")
    parser.add_argument("--batch", default="",
        help="JSON list of jobs: prompt, seed, width, height, steps, "
        "guidance, out name. One model load serves every job.")
    parser.add_argument("--image-path")
    parser.add_argument("--mask-path")
    parser.add_argument("--strength", type=float)
    parser.add_argument("--active-rect")
    parser.add_argument("--runtime-root", required=True)
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--width", type=int, default=512)
    parser.add_argument("--height", type=int, default=512)
    parser.add_argument("--steps", type=int, default=4)
    parser.add_argument("--seed", type=int, default=1234)
    parser.add_argument("--guidance", type=float, default=5.0)
    parser.add_argument("--dtype", type=str, default="bfloat16")
    args = parser.parse_args()

    model_path = Path(args.model_path)
    if not model_path.exists():
        _emit_result("failed", reason=f"Missing model path: {model_path}")
        return 1
    if not args.prompt and not args.batch:
        _emit_result("failed", reason="Need --prompt or --batch")
        return 1

    image_path = Path(args.image_path) if args.image_path else None
    mask_path = Path(args.mask_path) if args.mask_path else None
    active_rect = None
    if args.active_rect:
        active_rect = json.loads(args.active_rect)

    if args.pipeline_action in {"img2img", "inpaint", "outpaint"}:
        if image_path is None or not image_path.exists():
            _emit_result(
                "failed",
                reason=(
                    f"Missing source image for {args.pipeline_action}: "
                    f"{image_path}"
                ),
            )
            return 1

    if args.pipeline_action in {"inpaint", "outpaint"}:
        if mask_path is None or not mask_path.exists():
            _emit_result(
                "failed",
                reason=(
                    f"Missing mask image for {args.pipeline_action}: "
                    f"{mask_path}"
                ),
            )
            return 1

    if args.version == "Z-Image Turbo":
        supported_actions = _zimage_supported_pipeline_actions()
        if args.pipeline_action not in supported_actions:
            _emit_result(
                "unsupported",
                reason=(
                    "Z-Image Turbo service runtime does not expose "
                    f"{args.pipeline_action}; supported actions: "
                    f"{', '.join(supported_actions)}"
                ),
                supported_actions=supported_actions,
            )
            return 0

    cuda_ready, reason = _cuda_ready()
    if not cuda_ready:
        _emit_result("skipped", reason=reason)
        return 0

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
        pipeline_action=args.pipeline_action,
        width=args.width,
        height=args.height,
        steps=args.steps,
        dtype=args.dtype,
    )

    app = None
    try:
        app = ServiceApp(
            start_headless_api_server=False,
            initialize_headless_lifecycle=True,
        )
        client = LocalFallbackArtClient(signal_source=app)
        jobs = _batch_jobs(args)
        failures = 0
        for job in jobs:
            progress_updates = []
            response = client.invoke_with_progress(
                _build_request(
                    model_path=model_path,
                    version=args.version,
                    scheduler=args.scheduler,
                    prompt=job["prompt"],
                    pipeline_action=args.pipeline_action,
                    image_path=image_path,
                    mask_path=mask_path,
                    strength=args.strength,
                    active_rect=active_rect,
                    width=job["width"],
                    height=job["height"],
                    steps=job["steps"],
                    seed=job["seed"],
                    guidance=job["guidance"],
                ),
                progress_updates.append,
            )
            if response.status is not EnvelopeStatus.SUCCEEDED:
                _emit_result(
                    "failed",
                    reason="Art invocation did not succeed",
                    response_status=response.status.value,
                    out=job["out"],
                )
                failures += 1
                continue

            images = response.payload.get("images") or []
            if not images:
                _emit_result(
                    "failed",
                    reason="Art invocation returned no images",
                    response_status=response.status.value,
                    out=job["out"],
                )
                failures += 1
                continue

            raw_image = base64.b64decode(images[0])
            saved_path = output_root / job["out"]
            saved_path.write_bytes(raw_image)
            with Image.open(io.BytesIO(raw_image)) as image:
                _emit_result(
                    "succeeded",
                    response_status=response.status.value,
                    image_count=len(images),
                    image_size=list(image.size),
                    progress_count=len(progress_updates),
                    image_path=str(saved_path),
                    out=job["out"],
                )
        if failures and args.batch:
            _emit_result(
                "failed",
                reason=(
                    f"Batch failed: {failures} of {len(jobs)} "
                    "jobs failed"
                ),
                failures=failures,
                failure_count=failures,
                failed_count=failures,
                total_jobs=len(jobs),
            )
        return 1 if failures else 0
    except Exception as exc:
        _emit_result("failed", reason=str(exc))
        return 1
    finally:
        _cleanup_service_app(app)


if __name__ == "__main__":
    raise SystemExit(main())