"""Ollama metadata handlers extracted from the legacy HTTP server."""

from __future__ import annotations

import os
import re
from typing import Any, Callable


def handle_ollama_tags(handler: Any) -> None:
    """Handle the Ollama /api/tags endpoint."""
    metadata = configured_model_metadata(handler)
    handler._send_json_response(
        {
            "models": [
                {
                    "name": metadata["model_name"],
                    "model": metadata["model_name"],
                    "modified_at": "2024-12-01T00:00:00.000000000Z",
                    "size": metadata["size_bytes"],
                    "digest": model_digest(metadata["model_name"]),
                    "details": model_details(metadata),
                }
            ]
        }
    )


def handle_ollama_ps(
    handler: Any,
    *,
    get_api: Callable[..., Any],
) -> None:
    """Handle the Ollama /api/ps endpoint."""
    metadata = configured_model_metadata(handler)
    if not _ollama_model_loaded(get_api()):
        handler._send_json_response({"models": []})
        return
    handler._send_json_response({"models": [_ps_entry(metadata)]})


def handle_ollama_version(handler: Any) -> None:
    """Handle the Ollama /api/version endpoint."""
    handler._send_json_response({"version": "0.9.0"})


def handle_ollama_show(
    handler: Any,
    data: dict[str, Any],
    *,
    get_api: Callable[..., Any],
) -> None:
    """Handle the Ollama /api/show endpoint."""
    model_name = data.get("name", "airunner:latest")
    metadata = metadata_from_name(model_name)
    context_length = model_context_length(model_name.lower())
    handler._send_json_response(
        {
            "modelfile": modelfile_text(model_name, context_length),
            "parameters": f"temperature 0.7\nnum_ctx {context_length}",
            "template": model_template(),
            "license": "Apache 2.0",
            "modified_at": "2024-12-01T00:00:00.000000000Z",
            "details": model_details(metadata),
            "model_info": model_info(metadata, context_length),
            "capabilities": model_capabilities(model_name.lower()),
        }
    )


def configured_model_metadata(handler: Any) -> dict[str, Any]:
    """Return metadata for the configured local model, if any."""
    model_basename = configured_model_basename(handler)
    if not model_basename:
        return metadata_from_name("airunner:latest")
    return metadata_from_name(f"{model_basename}:latest")


def configured_model_basename(handler: Any) -> str:
    """Return the basename of the configured model path, if any."""
    try:
        from airunner_services.database.models.llm_generator_settings import (
            LLMGeneratorSettings,
        )

        settings = LLMGeneratorSettings.objects.first()
        if settings and settings.model_version:
            return os.path.basename(settings.model_version)
    except Exception as error:
        handler.logger.debug("Could not get model settings: %s", error)
    return ""


def metadata_from_name(model_name: str) -> dict[str, Any]:
    """Return family, size, and quantization metadata for a model name."""
    name_lower = model_name.lower()
    parameter_size = parameter_size_from_name(name_lower)
    quantization = quantization_from_name(name_lower)
    family = model_family(name_lower)
    return {
        "family": family,
        "families": [family],
        "model_name": model_name,
        "parameter_size": parameter_size,
        "quantization_level": quantization,
        "size_bytes": model_size_bytes(parameter_size, quantization),
    }


def model_family(name_lower: str) -> str:
    """Return the inferred Ollama family for a model name."""
    if "qwen" in name_lower:
        return "qwen"
    if "mistral" in name_lower:
        return "mistral"
    if "phi" in name_lower:
        return "phi"
    return "llama"


def parameter_size_from_name(name_lower: str) -> str:
    """Return the inferred parameter size for a model name."""
    size_match = re.search(r"(\d+\.?\d*)b", name_lower)
    if size_match:
        return f"{size_match.group(1).upper()}B"
    return "8B"


def quantization_from_name(name_lower: str) -> str:
    """Return the inferred quantization level for a model name."""
    if "4bit" in name_lower or "q4" in name_lower:
        return "Q4_K_M"
    if "8bit" in name_lower or "q8" in name_lower:
        return "Q8_0"
    if "fp16" in name_lower or "f16" in name_lower:
        return "F16"
    return "Q4_K_M"


def model_size_bytes(parameter_size: str, quantization: str) -> int:
    """Return an approximate byte size for one parameter count."""
    parameter_count = float(parameter_size.replace("B", ""))
    if quantization.startswith("Q4"):
        return int(parameter_count * 0.5 * 1e9)
    if quantization.startswith("Q8"):
        return int(parameter_count * 1.0 * 1e9)
    return int(parameter_count * 2.0 * 1e9)


def model_details(metadata: dict[str, Any]) -> dict[str, Any]:
    """Return the shared Ollama details payload."""
    return {
        "parent_model": "",
        "format": "gguf",
        "family": metadata["family"],
        "families": metadata["families"],
        "parameter_size": metadata["parameter_size"],
        "quantization_level": metadata["quantization_level"],
    }


def model_digest(model_name: str) -> str:
    """Return a deterministic placeholder digest for a model name."""
    digest = "".join(f"{ord(char):02x}" for char in model_name[:32])
    return f"sha256:{digest.ljust(64, '0')}"


def _ollama_model_loaded(api: Any) -> bool:
    """Return whether a model appears loaded for Ollama compatibility."""
    return bool(api is not None and hasattr(api, "llm") and api.llm is not None)


def _ps_entry(metadata: dict[str, Any]) -> dict[str, Any]:
    """Return the running-model entry for the /api/ps response."""
    return {
        "name": metadata["model_name"],
        "model": metadata["model_name"],
        "size": metadata["size_bytes"],
        "digest": model_digest(metadata["model_name"]),
        "details": model_details(metadata),
        "expires_at": "2099-12-31T23:59:59.000000000Z",
        "size_vram": metadata["size_bytes"],
    }


def model_capabilities(name_lower: str) -> list[str]:
    """Return the Ollama capabilities for a model name."""
    capabilities = ["completion", "tools"]
    if "-vl" in name_lower or "vl-" in name_lower or "vision" in name_lower:
        capabilities.append("vision")
    return capabilities


def model_context_length(name_lower: str) -> int:
    """Return the default context length for a model name."""
    if "qwen3" not in name_lower:
        return 4096
    if any(token in name_lower for token in ["30b", "235b", "4b"]):
        return 262144
    return 40960


def modelfile_text(model_name: str, context_length: int) -> str:
    """Return the simplified Ollama modelfile text."""
    return (
        f"FROM {model_name}\n"
        "PARAMETER temperature 0.7\n"
        f"PARAMETER num_ctx {context_length}"
    )


def model_template() -> str:
    """Return the placeholder Ollama chat template."""
    return (
        "{{ if .System }}<|im_start|>system\n{{ .System }}<|im_end|>\n"
        "{{ end }}{{ if .Prompt }}<|im_start|>user\n{{ .Prompt }}"
        "<|im_end|>\n{{ end }}<|im_start|>assistant\n{{ .Response }}"
        "<|im_end|>"
    )


def model_info(
    metadata: dict[str, Any],
    context_length: int,
) -> dict[str, Any]:
    """Return the Ollama show model_info payload."""
    return {
        "general.architecture": metadata["family"],
        "general.file_type": 15,
        "general.parameter_count": parameter_count(metadata["parameter_size"]),
        "general.quantization_version": 2,
        "tokenizer.ggml.model": "gpt2",
        "context_length": context_length,
    }


def parameter_count(parameter_size: str) -> int:
    """Return the integer parameter count for a parameter-size string."""
    cleaned = parameter_size.replace(".", "").replace("B", "")
    if cleaned.isdigit():
        return int(float(parameter_size.replace("B", "")) * 1e9)
    return 8000000000