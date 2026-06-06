"""Vision-input helpers for HuggingFace generation mixins."""

from __future__ import annotations

import io
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlparse

import torch
from PIL import Image as PILImage

from airunner_services.llm.adapters.mixins.generation_model_helpers import (
    get_model_dtype,
    is_quantized_model,
)
from airunner_services.llm.adapters.mixins.generation_vision_image_loading import (
    image_from_base64_string,
    image_from_data_url,
    image_from_file,
    image_from_remote_url,
)


def prepare_vision_inputs(
    adapter: Any,
    prompt: str,
    image_urls: list[Any],
) -> dict[str, torch.Tensor]:
    """Prepare multimodal inputs for one vision-capable adapter."""
    pil_images = collect_vision_images(adapter, image_urls)
    if not pil_images:
        return text_only_inputs(adapter, prompt)
    return processor_inputs(adapter, prompt, pil_images)


def collect_vision_images(
    adapter: Any,
    image_urls: list[Any],
) -> list[PILImage.Image]:
    """Load and normalize one list of image inputs."""
    pil_images: list[PILImage.Image] = []
    quantized = is_quantized_model(adapter)
    for source in image_urls:
        image = load_image_from_source(adapter, source)
        if image is None:
            adapter.logger.warning(
                "Skipping unusable image source for vision prompt"
            )
            continue
        pil_images.append(_normalized_image(adapter, image, quantized))
    return cap_quantized_images(adapter, pil_images, quantized)


def _normalized_image(
    adapter: Any,
    image: PILImage.Image,
    quantized: bool,
) -> PILImage.Image:
    """Return one image normalized for the current adapter mode."""
    if not quantized:
        return image
    return resize_image_for_quantized_model(adapter, image, max_size=768)


def cap_quantized_images(
    adapter: Any,
    pil_images: list[PILImage.Image],
    quantized: bool,
) -> list[PILImage.Image]:
    """Cap image count for quantized vision models."""
    if not quantized or len(pil_images) <= 4:
        return pil_images
    adapter.logger.info(
        "Quantized vision model: capping images to first 4 to avoid "
        "token bloat"
    )
    return pil_images[:4]


def text_only_inputs(
    adapter: Any,
    prompt: str,
) -> dict[str, torch.Tensor]:
    """Return tokenizer-only inputs when no usable images remain."""
    return adapter.tokenizer(
        prompt,
        return_tensors="pt",
        truncation=True,
        add_special_tokens=False,
    ).to(adapter.model.device)


def processor_inputs(
    adapter: Any,
    prompt: str,
    pil_images: list[PILImage.Image],
) -> dict[str, torch.Tensor]:
    """Return processor-backed multimodal tensors."""
    try:
        inputs = adapter.processor(
            text=prompt,
            images=pil_images,
            return_tensors="pt",
            padding=True,
            add_special_tokens=False,
        )
        inputs = {
            key: value.to(adapter.model.device)
            for key, value in inputs.items()
        }
        align_model_dtype(adapter, inputs)
        log_vision_inputs(adapter, pil_images, inputs)
        return inputs
    except Exception as error:
        adapter.logger.error("Failed to prepare vision inputs: %s", error)
        return text_only_inputs(adapter, prompt)


def align_model_dtype(
    adapter: Any,
    inputs: dict[str, torch.Tensor],
) -> None:
    """Align floating tensors with the live model dtype."""
    model_dtype = get_model_dtype(adapter)
    if model_dtype is None:
        return
    for key, tensor in inputs.items():
        if torch.is_floating_point(tensor) and tensor.dtype != model_dtype:
            inputs[key] = tensor.to(dtype=model_dtype)


def log_vision_inputs(
    adapter: Any,
    pil_images: list[PILImage.Image],
    inputs: dict[str, torch.Tensor],
) -> None:
    """Log one summary of prepared vision inputs."""
    pixel_values = inputs.get("pixel_values")
    pixel_dtype = pixel_values.dtype if pixel_values is not None else "n/a"
    adapter.logger.info(
        "Prepared vision inputs with %s image(s), input_ids shape: %s, "
        "pixel_values dtype: %s",
        len(pil_images),
        inputs["input_ids"].shape,
        pixel_dtype,
    )


def resize_image_for_quantized_model(
    adapter: Any,
    image: PILImage.Image,
    max_size: int = 768,
) -> PILImage.Image:
    """Resize oversized images for quantized vision models."""
    if image.width <= max_size and image.height <= max_size:
        return image
    resized = image.copy()
    resized.thumbnail((max_size, max_size), PILImage.LANCZOS)
    adapter.logger.info(
        "Resizing image from %s to %s for quantized model compatibility",
        image.size,
        resized.size,
    )
    return resized


def load_image_from_source(
    adapter: Any,
    source: Any,
) -> Optional[PILImage.Image]:
    """Best-effort conversion of common image sources to PIL images."""
    if source is None:
        return None
    if isinstance(source, PILImage.Image):
        return source.convert("RGB")
    if isinstance(source, (bytes, bytearray)):
        return PILImage.open(io.BytesIO(source)).convert("RGB")
    if isinstance(source, dict):
        return _image_from_mapping(adapter, source)
    if isinstance(source, (str, Path)):
        return _image_from_string_source(adapter, str(source))
    return None


def _image_from_mapping(
    adapter: Any,
    source: dict[str, Any],
) -> Optional[PILImage.Image]:
    """Resolve one image from a mapping-style payload."""
    data_candidate = (
        source.get("data")
        or source.get("image")
        or source.get("content")
        or source.get("bytes")
    )
    path_candidate = source.get("path") or source.get("url")
    if data_candidate:
        return load_image_from_source(adapter, data_candidate)
    if path_candidate:
        return load_image_from_source(adapter, path_candidate)
    return None


def _image_from_string_source(
    adapter: Any,
    path_str: str,
) -> Optional[PILImage.Image]:
    """Resolve one image from a string source."""
    if path_str.startswith("data:image"):
        return image_from_data_url(path_str)
    parsed = urlparse(path_str)
    if parsed.scheme in {"http", "https"}:
        return image_from_remote_url(adapter, path_str)
    fs_image = image_from_file(adapter, path_str)
    if fs_image is not None:
        return fs_image
    return image_from_base64_string(path_str)
