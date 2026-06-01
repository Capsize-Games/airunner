"""Art-job compatibility handlers extracted from the legacy HTTP server."""

from __future__ import annotations

import glob
import io
import os
import threading
import time
import uuid
from typing import Any

from airunner_services.art.managers.stablediffusion.image_response import (
    ImageResponse,
)
from airunner_services.contract_enums import SignalCode


def handle_art_v1_generate(
    handler: Any,
    data: dict[str, Any],
    *,
    art_jobs: dict[str, dict[str, Any]],
    art_jobs_lock: threading.Lock,
) -> None:
    """Start one compatibility art generation job."""
    handler._purge_old_art_jobs()
    prompt = (data.get("prompt") or "").strip()
    if not prompt:
        handler._send_json_response({"error": "Missing 'prompt' field"}, status=400)
        return
    model_path = requested_model_path(data)
    success, error_msg = handler._ensure_art_model_loaded(model_path=model_path)
    if not success:
        _send_art_model_unavailable(handler, error_msg)
        return
    job_id = uuid.uuid4().hex
    _initialize_art_job(art_jobs, art_jobs_lock, job_id)
    payload = native_art_payload(data, prompt, model_path)
    _start_art_job_thread(handler, art_jobs, art_jobs_lock, job_id, payload)
    handler._send_json_response({"job_id": job_id, "status": "pending"}, status=200)


def handle_art_v1_status(
    handler: Any,
    job_id: str,
    *,
    art_jobs: dict[str, dict[str, Any]],
    art_jobs_lock: threading.Lock,
) -> None:
    """Return the status for one compatibility art generation job."""
    handler._purge_old_art_jobs()
    if not job_id:
        handler._send_json_response({"error": "Missing job_id"}, status=400)
        return
    job = _art_job(art_jobs, art_jobs_lock, job_id)
    if job is None:
        handler._send_json_response({"error": "Job not found", "status": "not_found"}, status=404)
        return
    payload = {"job_id": job_id, "status": job.get("status") or "pending"}
    if job.get("error"):
        payload["error"] = job.get("error")
    handler._send_json_response(payload, status=200)


def handle_art_v1_result(
    handler: Any,
    job_id: str,
    *,
    art_jobs: dict[str, dict[str, Any]],
    art_jobs_lock: threading.Lock,
) -> None:
    """Return the PNG bytes for one completed compatibility job."""
    handler._purge_old_art_jobs()
    if not job_id:
        handler._send_json_response({"error": "Missing job_id"}, status=400)
        return
    job = _art_job(art_jobs, art_jobs_lock, job_id)
    if job is None:
        handler._send_json_response({"error": "Job not found"}, status=404)
        return
    status_value = str(job.get("status") or "pending").lower()
    if status_value != "completed":
        _send_job_not_ready(handler, status_value)
        return
    png_bytes = job.get("png_bytes") or b""
    if not png_bytes:
        handler._send_json_response({"error": "No image bytes available"}, status=500)
        return
    handler._send_bytes_response(png_bytes, status=200, content_type="image/png")


def handle_art_v1_models(handler: Any) -> None:
    """List local art model files for compatibility clients."""
    base_dir = first_existing_directory(candidate_model_directories())
    models = [model_entry(path) for path in model_files(base_dir) if model_entry(path)]
    handler._send_json_response({"base_dir": base_dir, "models": models}, status=200)


def generate_first_png_bytes(
    handler: Any,
    data: dict[str, Any],
    *,
    get_api: Any,
) -> bytes:
    """Run a native art request and return the first PNG bytes."""
    complete_event = threading.Event()
    result_holder = {"response": None, "error": None}
    image_request = handler._create_image_request(data)
    image_request.callback = completion_callback(result_holder, complete_event)
    api = get_api()
    if not api:
        raise RuntimeError("API not initialized")
    api.emit_signal(SignalCode.DO_GENERATE_SIGNAL, {"image_request": image_request})
    if not complete_event.wait(timeout=300):
        raise RuntimeError("Image generation timeout")
    if result_holder.get("error"):
        raise RuntimeError(str(result_holder["error"]))
    return first_png_bytes(result_holder.get("response"))


def requested_model_path(data: dict[str, Any]) -> str | None:
    """Return the optional per-request art model path override."""
    model_path = (data.get("model_path") or "").strip()
    return model_path or None


def native_art_payload(
    data: dict[str, Any],
    prompt: str,
    model_path: str | None,
) -> dict[str, Any]:
    """Return the native /art payload mirrored from a compat request."""
    payload = {
        "prompt": prompt,
        "negative_prompt": data.get("negative_prompt") or "",
        "width": int(data.get("width") or 1024),
        "height": int(data.get("height") or 1024),
        "steps": int(data.get("steps") or 20),
        "scale": art_scale(data),
        "seed": art_seed(data),
        "random_seed": data.get("seed") is None,
        "n_samples": int(data.get("num_images") or 1),
        "images_per_batch": int(data.get("num_images") or 1),
    }
    if model_path:
        payload["model_path"] = model_path
    return payload


def art_scale(data: dict[str, Any]) -> float:
    """Return the scale field for a compatibility art request."""
    if data.get("cfg_scale") is not None:
        return float(data["cfg_scale"])
    return float(data.get("scale") or 7.5)


def art_seed(data: dict[str, Any]) -> int:
    """Return the seed field for a compatibility art request."""
    if data.get("seed") is None:
        return 42
    return int(data.get("seed") or 42)


def _send_art_model_unavailable(handler: Any, error_msg: str) -> None:
    """Send the standard unavailable-art-model response."""
    handler._send_json_response(
        {
            "error": "Art model not available",
            "details": error_msg,
            "hint": "Start with --enable-art flag and configure an art model",
        },
        status=503,
    )


def _initialize_art_job(
    art_jobs: dict[str, dict[str, Any]],
    art_jobs_lock: threading.Lock,
    job_id: str,
) -> None:
    """Create one pending art job entry."""
    with art_jobs_lock:
        art_jobs[job_id] = {
            "job_id": job_id,
            "status": "pending",
            "created_at": time.time(),
            "error": "",
            "png_bytes": b"",
        }


def _start_art_job_thread(
    handler: Any,
    art_jobs: dict[str, dict[str, Any]],
    art_jobs_lock: threading.Lock,
    job_id: str,
    payload: dict[str, Any],
) -> None:
    """Start the background thread that completes one art job."""
    thread = threading.Thread(
        target=_run_art_job,
        args=(handler, art_jobs, art_jobs_lock, job_id, payload),
        daemon=True,
    )
    thread.start()


def _run_art_job(
    handler: Any,
    art_jobs: dict[str, dict[str, Any]],
    art_jobs_lock: threading.Lock,
    job_id: str,
    payload: dict[str, Any],
) -> None:
    """Execute one background art job and store the result."""
    try:
        png_bytes = handler._generate_first_png_bytes(payload)
        _update_art_job(art_jobs, art_jobs_lock, job_id, status="completed", png_bytes=png_bytes)
    except Exception as error:
        _update_art_job(art_jobs, art_jobs_lock, job_id, status="failed", error=str(error))


def _update_art_job(
    art_jobs: dict[str, dict[str, Any]],
    art_jobs_lock: threading.Lock,
    job_id: str,
    *,
    status: str,
    png_bytes: bytes = b"",
    error: str = "",
) -> None:
    """Update one art job entry when the background work finishes."""
    with art_jobs_lock:
        job = art_jobs.get(job_id)
        if job is None:
            return
        job["status"] = status
        job["png_bytes"] = png_bytes
        job["error"] = error


def _art_job(
    art_jobs: dict[str, dict[str, Any]],
    art_jobs_lock: threading.Lock,
    job_id: str,
) -> dict[str, Any] | None:
    """Return one art job entry by id."""
    with art_jobs_lock:
        return art_jobs.get(job_id)


def _send_job_not_ready(handler: Any, status_value: str) -> None:
    """Send the standard not-ready response for a job result request."""
    handler._send_json_response(
        {"error": f"Job not completed (status={status_value})"},
        status=409,
    )


def candidate_model_directories() -> list[str]:
    """Return candidate directories that may contain art model files."""
    env_path = (os.environ.get("AIRUNNER_ART_MODEL_PATH") or "").strip()
    directories: list[str] = []
    if env_path and os.path.isdir(env_path):
        directories.append(env_path)
    elif env_path and os.path.isfile(env_path):
        directories.append(os.path.dirname(env_path))
    directories.extend(
        [
            "/home/airunner/.local/share/airunner/art/models/Z-Image Turbo/txt2img",
            "/home/joe/.local/share/airunner/art/models/Z-Image Turbo/txt2img",
            os.path.join(
                os.path.expanduser("~"),
                ".local",
                "share",
                "airunner",
                "art",
                "models",
                "Z-Image Turbo",
                "txt2img",
            ),
        ]
    )
    return directories


def first_existing_directory(directories: list[str]) -> str:
    """Return the first existing directory from a list of candidates."""
    for directory in directories:
        if os.path.isdir(directory):
            return directory
    return ""


def model_files(base_dir: str) -> list[str]:
    """Return the safetensors model files found in one base directory."""
    if not base_dir:
        return []
    return sorted(glob.glob(os.path.join(base_dir, "*.safetensors")))


def model_entry(path: str) -> dict[str, Any] | None:
    """Return one model listing entry for a safetensors file."""
    try:
        stats = os.stat(path)
    except Exception:
        return None
    return {
        "id": path,
        "name": os.path.basename(path),
        "path": path,
        "size_bytes": int(stats.st_size),
    }


def completion_callback(
    result_holder: dict[str, Any],
    complete_event: threading.Event,
) -> Any:
    """Return the completion callback for native art generation."""
    def on_complete(response: Any) -> None:
        if isinstance(response, ImageResponse):
            result_holder["response"] = response
        elif isinstance(response, str):
            result_holder["error"] = response
        else:
            result_holder["response"] = response
        complete_event.set()

    return on_complete


def first_png_bytes(response: Any) -> bytes:
    """Return the first PNG bytes from a native image generation response."""
    images = response_images(response)
    if not images or images[0] is None:
        raise RuntimeError("No image returned")
    buffer = io.BytesIO()
    images[0].save(buffer, format="PNG")
    return buffer.getvalue()


def response_images(response: Any) -> list[Any]:
    """Return the image list from an ImageResponse or dict payload."""
    if isinstance(response, ImageResponse):
        return response.images or []
    if isinstance(response, dict):
        return response.get("images") or []
    return []