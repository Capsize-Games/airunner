"""Conditioned art runtime tests for the direct service boundary."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from PIL import Image, ImageDraw

os.environ.setdefault("AIRUNNER_TEST_NO_GUI_LAUNCH", "1")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


_SERVICES_ROOT = Path(__file__).resolve().parents[3]
_PROJECT_ROOT = _SERVICES_ROOT.parent.parent.parent

for _path in (
    _PROJECT_ROOT / "services" / "src",
    _PROJECT_ROOT / "src",
):
    _path_str = str(_path)
    if _path_str not in sys.path:
        sys.path.append(_path_str)


from airunner_services.contract_enums import Scheduler, StableDiffusionVersion

_PROBE_RESULT_PREFIX = "ART_RUNTIME_RESULT:"
pytestmark = [pytest.mark.art_service_runtime]


def _art_models_root() -> Path:
    return Path.home() / ".local" / "share" / "airunner" / "art" / "models"


def _first_model_file(search_dir: Path) -> Path | None:
    for extension in ("*.safetensors", "*.ckpt", "*.gguf"):
        candidates = sorted(search_dir.glob(extension))
        if candidates:
            return candidates[0]
    return None


def _require_model_file(version: str, pipeline_action: str) -> Path:
    version_dir = _art_models_root() / version
    if not version_dir.is_dir():
        pytest.skip(f"Missing local art model directory: {version_dir}")

    preferred_dir = version_dir / pipeline_action
    if preferred_dir.is_dir():
        preferred_model = _first_model_file(preferred_dir)
        if preferred_model is not None:
            return preferred_model

    for action_dir in sorted(
        path for path in version_dir.iterdir() if path.is_dir()
    ):
        candidate = _first_model_file(action_dir)
        if candidate is not None:
            return candidate

    candidate = _first_model_file(version_dir)
    if candidate is not None:
        return candidate

    pytest.skip(f"No model file found under {version_dir}")


def _probe_script_path() -> Path:
    return Path(__file__).with_name("art_service_runtime_probe.py")


def _run_runtime_probe(
    *,
    tmp_path: Path,
    model_path: Path,
    version: str,
    scheduler: str,
    pipeline_action: str,
    prompt: str,
    image_path: Path | None = None,
    mask_path: Path | None = None,
    strength: float | None = None,
    active_rect: dict[str, int] | None = None,
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

    command = [
        sys.executable,
        str(_probe_script_path()),
        "--model-path",
        str(model_path),
        "--version",
        version,
        "--scheduler",
        scheduler,
        "--pipeline-action",
        pipeline_action,
        "--prompt",
        prompt,
        "--runtime-root",
        str(Path.home() / ".local" / "share" / "airunner"),
        "--output-root",
        str(output_root),
    ]
    if image_path is not None:
        command.extend(["--image-path", str(image_path)])
    if mask_path is not None:
        command.extend(["--mask-path", str(mask_path)])
    if strength is not None:
        command.extend(["--strength", str(strength)])
    if active_rect is not None:
        command.extend(["--active-rect", json.dumps(active_rect)])

    completed = subprocess.run(
        command,
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


def _write_source_image(image_path: Path) -> None:
    image = Image.new("RGB", (512, 512), "#1f3b4d")
    draw = ImageDraw.Draw(image)
    draw.rectangle((64, 64, 448, 448), fill="#f4a261")
    draw.ellipse((144, 112, 368, 336), fill="#e9c46a")
    draw.rectangle((176, 336, 336, 448), fill="#2a9d8f")
    image.save(image_path)


def _write_inpaint_mask(mask_path: Path) -> None:
    mask = Image.new("RGB", (512, 512), "black")
    draw = ImageDraw.Draw(mask)
    draw.ellipse((176, 144, 336, 304), fill="white")
    mask.save(mask_path)


def _write_outpaint_mask(mask_path: Path) -> None:
    mask = Image.new("RGB", (512, 512), "black")
    draw = ImageDraw.Draw(mask)
    draw.rectangle((384, 0, 511, 511), fill="white")
    mask.save(mask_path)


def _active_rect() -> dict[str, int]:
    return {"x": 0, "y": 0, "width": 512, "height": 512}


def _assert_success(result: dict[str, object]) -> None:
    assert result["status"] == "succeeded"
    assert result["response_status"] == "succeeded"
    assert result["image_count"] == 1
    assert result["image_size"] == [512, 512]
    assert result["progress_count"] >= 1


@pytest.mark.gpu
@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.timeout(600)
def test_sdxl_img2img_generates_image_through_direct_service_runtime(
    tmp_path: Path,
) -> None:
    """SDXL img2img succeeds through the direct service runtime boundary."""
    model_path = _require_model_file(
        StableDiffusionVersion.SDXL1_0.value,
        "img2img",
    )
    image_path = tmp_path / "sdxl-img2img-source.png"
    _write_source_image(image_path)

    result = _run_runtime_probe(
        tmp_path=tmp_path,
        model_path=model_path,
        version=StableDiffusionVersion.SDXL1_0.value,
        scheduler=Scheduler.EULER.value,
        pipeline_action="img2img",
        prompt="Turn this scene into a cinematic oil painting.",
        image_path=image_path,
        strength=0.65,
    )

    _assert_success(result)


@pytest.mark.gpu
@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.timeout(600)
def test_sdxl_inpaint_generates_image_through_direct_service_runtime(
    tmp_path: Path,
) -> None:
    """SDXL inpaint succeeds through the direct service runtime boundary."""
    model_path = _require_model_file(
        StableDiffusionVersion.SDXL1_0.value,
        "inpaint",
    )
    image_path = tmp_path / "sdxl-inpaint-source.png"
    mask_path = tmp_path / "sdxl-inpaint-mask.png"
    _write_source_image(image_path)
    _write_inpaint_mask(mask_path)

    result = _run_runtime_probe(
        tmp_path=tmp_path,
        model_path=model_path,
        version=StableDiffusionVersion.SDXL1_0.value,
        scheduler=Scheduler.EULER.value,
        pipeline_action="inpaint",
        prompt="Replace the masked area with a glass lantern.",
        image_path=image_path,
        mask_path=mask_path,
        strength=0.7,
    )

    _assert_success(result)


@pytest.mark.gpu
@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.timeout(600)
def test_sdxl_outpaint_generates_image_through_direct_service_runtime(
    tmp_path: Path,
) -> None:
    """SDXL outpaint succeeds through the direct service runtime boundary."""
    model_path = _require_model_file(
        StableDiffusionVersion.SDXL1_0.value,
        "outpaint",
    )
    image_path = tmp_path / "sdxl-outpaint-source.png"
    mask_path = tmp_path / "sdxl-outpaint-mask.png"
    _write_source_image(image_path)
    _write_outpaint_mask(mask_path)

    result = _run_runtime_probe(
        tmp_path=tmp_path,
        model_path=model_path,
        version=StableDiffusionVersion.SDXL1_0.value,
        scheduler=Scheduler.EULER.value,
        pipeline_action="outpaint",
        prompt="Extend the scene into a misty seaside promenade.",
        image_path=image_path,
        mask_path=mask_path,
        strength=0.7,
        active_rect=_active_rect(),
    )

    _assert_success(result)


@pytest.mark.gpu
@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.timeout(600)
def test_zimage_img2img_generates_image_through_direct_service_runtime(
    tmp_path: Path,
) -> None:
    """Z-Image img2img succeeds through the direct service runtime boundary."""
    model_path = _require_model_file(
        StableDiffusionVersion.Z_IMAGE_TURBO.value,
        "img2img",
    )
    image_path = tmp_path / "zimage-img2img-source.png"
    _write_source_image(image_path)

    result = _run_runtime_probe(
        tmp_path=tmp_path,
        model_path=model_path,
        version=StableDiffusionVersion.Z_IMAGE_TURBO.value,
        scheduler=Scheduler.FLOW_MATCH_EULER.value,
        pipeline_action="img2img",
        prompt="Transform this artwork into a crisp sci-fi illustration.",
        image_path=image_path,
        strength=0.6,
    )

    _assert_success(result)


@pytest.mark.integration
def test_zimage_inpaint_reports_unsupported_service_capability(
    tmp_path: Path,
) -> None:
    """Z-Image inpaint is not exposed by the service-owned manager."""
    model_path = _require_model_file(
        StableDiffusionVersion.Z_IMAGE_TURBO.value,
        "inpaint",
    )
    image_path = tmp_path / "zimage-inpaint-source.png"
    mask_path = tmp_path / "zimage-inpaint-mask.png"
    _write_source_image(image_path)
    _write_inpaint_mask(mask_path)

    result = _run_runtime_probe(
        tmp_path=tmp_path,
        model_path=model_path,
        version=StableDiffusionVersion.Z_IMAGE_TURBO.value,
        scheduler=Scheduler.FLOW_MATCH_EULER.value,
        pipeline_action="inpaint",
        prompt="Replace the masked area with glowing runes.",
        image_path=image_path,
        mask_path=mask_path,
        strength=0.6,
    )

    assert result["status"] == "unsupported"
    assert "supported actions" in str(result["reason"])


@pytest.mark.integration
def test_zimage_outpaint_reports_unsupported_service_capability(
    tmp_path: Path,
) -> None:
    """Z-Image outpaint is not exposed by the service-owned manager."""
    model_path = _require_model_file(
        StableDiffusionVersion.Z_IMAGE_TURBO.value,
        "outpaint",
    )
    image_path = tmp_path / "zimage-outpaint-source.png"
    mask_path = tmp_path / "zimage-outpaint-mask.png"
    _write_source_image(image_path)
    _write_outpaint_mask(mask_path)

    result = _run_runtime_probe(
        tmp_path=tmp_path,
        model_path=model_path,
        version=StableDiffusionVersion.Z_IMAGE_TURBO.value,
        scheduler=Scheduler.FLOW_MATCH_EULER.value,
        pipeline_action="outpaint",
        prompt="Extend the city skyline into the masked area.",
        image_path=image_path,
        mask_path=mask_path,
        strength=0.6,
        active_rect=_active_rect(),
    )

    assert result["status"] == "unsupported"
    assert "supported actions" in str(result["reason"])
