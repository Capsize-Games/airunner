"""
Complete model download and quantization pipeline for AI Runner.

This module provides a unified interface for:
1. Downloading models from HuggingFace
2. Quantizing models to 2-bit or 4-bit
3. Cleaning up temporary files
4. Managing model registry
"""

import logging
import os
import shutil
from pathlib import Path
from typing import Optional, Callable
import json

from airunner.components.llm.utils.model_downloader import (
    HuggingFaceDownloader,
)
from airunner.components.llm.utils.model_quantizer import ModelQuantizer
from airunner.settings import AIRUNNER_LOG_LEVEL
from airunner.utils.application import get_logger
from airunner.components.application.gui.windows.main.settings_mixin import (
    SettingsMixin,
)
from airunner.utils.application.mediator_mixin import MediatorMixin

logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)


class ModelPipeline(
    MediatorMixin,
    SettingsMixin,
):
    """
    Unified pipeline for downloading and quantizing LLM models.

    Workflow:
    1. Download model from HuggingFace → temp directory
    2. Quantize to 4-bit (recommended) → final directory
    3. Optionally quantize to 2-bit → final directory
    4. Clean up unquantized files
    5. Update model registry
    """

    # Supported models with their characteristics
    SUPPORTED_MODELS = {
        "ministral3-8b": {
            "repo_id": "mistralai/Ministral-3-8B-Instruct-2512",
            "model_type": "ministral3",
            "supports_function_calling": True,
            "vision_capable": True,
            "context_length": 262144,  # 256K context
            "vram_requirements_gb": {
                "full": 24,
                "4bit": 8,
                "2bit": 4,
            },
            "recommended_bits": 4,
        },
        "qwen2.5-7b": {
            "repo_id": "Qwen/Qwen2.5-7B-Instruct",
            "model_type": "llm",
            "supports_function_calling": True,
            "context_length": 32768,
            "vram_requirements_gb": {
                "full": 28,
                "4bit": 7,
                "2bit": 4,
            },
            "recommended_bits": 4,
        },
        "qwen3-8b": {
            "repo_id": "Qwen/Qwen3-8B-GGUF",
            "gguf_filename": "Qwen3-8B-Q4_K_M.gguf",
            "model_type": "llm",
            "supports_function_calling": True,
            "supports_thinking": True,
            "context_length": 32768,
            "native_context_length": 32768,
            "yarn_max_context_length": 131072,
            "vram_requirements_gb": {
                "full": 32,
                "4bit": 8,
                "2bit": 5,
            },
            "recommended_bits": 4,
        },
    }

    def __init__(self, base_path: Optional[str] = None):
        """
        Initialize pipeline.

        Args:
            base_path: Base directory for models (default: ~/.local/share/airunner/text/models/llm)
        """
        super().__init__()
        if base_path is None:
            base_path = os.path.join(
                os.path.expanduser(self.path_settings.base_path),
                f"text/models/llm",
            )

        self.base_path = Path(base_path)
        self.downloads_dir = (
            self.base_path / "causallm"
        )  # Download directly to causallm
        self.models_dir = self.base_path / "causallm"
        self.registry_file = self.base_path / "registry.json"

        # Create directories
        self.downloads_dir.mkdir(parents=True, exist_ok=True)
        self.models_dir.mkdir(parents=True, exist_ok=True)

        # Initialize components
        self.downloader = HuggingFaceDownloader(
            cache_dir=str(self.downloads_dir)
        )
        self.quantizer = ModelQuantizer()

        # Load or create registry
        self.registry = self._load_registry()

    def download_and_quantize(
        self,
        model_key: str,
        quantize_4bit: bool = True,
        quantize_2bit: bool = False,
        keep_unquantized: bool = False,
        progress_callback: Optional[Callable[[str, float], None]] = None,
    ) -> dict:
        """
        Complete pipeline: download model and create quantized versions.

        Args:
            model_key: Model key from SUPPORTED_MODELS (e.g., "ministral3-8b")
            quantize_4bit: Create 4-bit quantized version (recommended)
            quantize_2bit: Create 2-bit quantized version (maximum compression)
            keep_unquantized: Keep full-precision model after quantization
            progress_callback: Callback(stage_description, progress_0_to_1)

        Returns:
            Dict with paths to created model variants
        """
        if model_key not in self.SUPPORTED_MODELS:
            raise ValueError(
                f"Unsupported model: {model_key}. "
                f"Supported: {list(self.SUPPORTED_MODELS.keys())}"
            )

        model_info = self.SUPPORTED_MODELS[model_key]
        repo_id = model_info["repo_id"]
        model_name = repo_id.split("/")[-1]

        logger.info(f"Starting pipeline for {model_key} ({repo_id})")

        results = {}

        # Step 1: Download model
        if progress_callback:
            progress_callback(f"Downloading {model_name}", 0.0)

        download_path = self.downloader.download_model(
            repo_id=repo_id,
            model_type=model_info["model_type"],
            include_patterns=["*.safetensors", "*.json"],
            exclude_patterns=["*.bin", "*.msgpack", "*consolidated*"],
            progress_callback=lambda f, d, t: (
                progress_callback(
                    f"Downloading {f}", 0.0 + (0.4 * d / t) if t > 0 else 0.0
                )
                if progress_callback
                else None
            ),
        )

        results["downloaded"] = str(download_path)

        # Step 2: Quantize to 4-bit
        if quantize_4bit:
            if progress_callback:
                progress_callback(f"Quantizing {model_name} to 4-bit", 0.4)

            output_4bit = self.models_dir / f"{model_name}-4bit-gptq"

            self.quantizer.quantize_model(
                model_path=str(download_path),
                output_path=str(output_4bit),
                bits=4,
                progress_callback=lambda stage, pct: (
                    progress_callback(f"4-bit: {stage}", 0.4 + (0.3 * pct))
                    if progress_callback
                    else None
                ),
            )

            results["4bit"] = str(output_4bit)

            # Update registry
            self._add_to_registry(
                model_key=f"{model_key}-4bit",
                path=str(output_4bit),
                model_info=model_info,
                quantization="4bit",
            )

        # Step 3: Quantize to 2-bit (optional)
        if quantize_2bit:
            if progress_callback:
                progress_callback(f"Quantizing {model_name} to 2-bit", 0.7)

            output_2bit = self.models_dir / f"{model_name}-2bit-gptq"

            self.quantizer.quantize_model(
                model_path=str(download_path),
                output_path=str(output_2bit),
                bits=2,
                progress_callback=lambda stage, pct: (
                    progress_callback(f"2-bit: {stage}", 0.7 + (0.2 * pct))
                    if progress_callback
                    else None
                ),
            )

            results["2bit"] = str(output_2bit)

            # Update registry
            self._add_to_registry(
                model_key=f"{model_key}-2bit",
                path=str(output_2bit),
                model_info=model_info,
                quantization="2bit",
            )

        # Step 4: Clean up unquantized model (unless requested to keep)
        if not keep_unquantized:
            if progress_callback:
                progress_callback("Cleaning up temporary files", 0.9)

            logger.info(f"Removing unquantized model: {download_path}")
            shutil.rmtree(download_path)
        else:
            results["unquantized"] = str(download_path)

        if progress_callback:
            progress_callback("Complete", 1.0)

        logger.info(f"Pipeline complete for {model_key}")
        logger.info(f"Results: {results}")

        return results

    def download_from_url(
        self,
        url: str,
        quantize_4bit: bool = True,
        quantize_2bit: bool = False,
        progress_callback: Optional[Callable[[str, float], None]] = None,
    ) -> dict:
        """
        Download and quantize a model from a HuggingFace URL.

        Args:
            url: HuggingFace model URL (e.g., "https://huggingface.co/mistralai/Ministral-3-8B-Instruct-2512")
            quantize_4bit: Create 4-bit version
            quantize_2bit: Create 2-bit version
            progress_callback: Callback(stage_description, progress_0_to_1)

        Returns:
            Dict with paths to created model variants
        """
        # Extract repo_id from URL
        # URL format: https://huggingface.co/{owner}/{model_name}
        if "//" in url:
            url = url.split("//")[1]  # Remove protocol

        parts = url.split("/")
        if "huggingface.co" in parts:
            idx = parts.index("huggingface.co")
            repo_id = "/".join(parts[idx + 1 : idx + 3])
        else:
            raise ValueError(f"Invalid HuggingFace URL: {url}")

        logger.info(f"Extracted repo_id: {repo_id}")

        # Check if it's a known model
        for key, info in self.SUPPORTED_MODELS.items():
            if info["repo_id"] == repo_id:
                logger.info(f"Recognized model: {key}")
                return self.download_and_quantize(
                    model_key=key,
                    quantize_4bit=quantize_4bit,
                    quantize_2bit=quantize_2bit,
                    progress_callback=progress_callback,
                )

        # Unknown model - try to download anyway (assume "llm" type)
        logger.warning(f"Unknown model: {repo_id}. Attempting download...")

        model_name = repo_id.split("/")[-1]

        # Download
        download_path = self.downloader.download_model(
            repo_id=repo_id,
            model_type="llm",
            include_patterns=["*.safetensors", "*.json"],
            exclude_patterns=["*.bin", "*.msgpack", "*consolidated*"],
            progress_callback=lambda f, d, t: (
                progress_callback(
                    f"Downloading {f}", 0.0 + (0.5 * d / t) if t > 0 else 0.0
                )
                if progress_callback
                else None
            ),
        )

        results = {"downloaded": str(download_path)}

        # Quantize if requested
        if quantize_4bit:
            output_4bit = self.models_dir / f"{model_name}-4bit-gptq"
            self.quantizer.quantize_model(
                model_path=str(download_path),
                output_path=str(output_4bit),
                bits=4,
                progress_callback=lambda stage, pct: (
                    progress_callback(f"4-bit: {stage}", 0.5 + (0.5 * pct))
                    if progress_callback
                    else None
                ),
            )
            results["4bit"] = str(output_4bit)

        return results

    def list_available_models(self) -> dict:
        """
        List all supported models and their requirements.

        Returns:
            Dict of model info
        """
        return self.SUPPORTED_MODELS.copy()

    def list_downloaded_models(self) -> list:
        """
        List models that have been downloaded.

        Returns:
            List of model info dicts from registry
        """
        return list(self.registry.values())

    def _load_registry(self) -> dict:
        """Load model registry from disk."""
        if self.registry_file.exists():
            try:
                with open(self.registry_file) as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load registry: {e}")
                return {}
        return {}

    def _save_registry(self):
        """Save model registry to disk."""
        try:
            with open(self.registry_file, "w") as f:
                json.dump(self.registry, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save registry: {e}")

    def _add_to_registry(
        self,
        model_key: str,
        path: str,
        model_info: dict,
        quantization: str,
    ):
        """Add a model to the registry."""
        self.registry[model_key] = {
            "path": path,
            "repo_id": model_info["repo_id"],
            "quantization": quantization,
            "supports_function_calling": model_info[
                "supports_function_calling"
            ],
            "context_length": model_info["context_length"],
            "vram_gb": model_info["vram_requirements_gb"][quantization],
        }
        self._save_registry()


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    pipeline = ModelPipeline()

    # List available models
    print("Available models:")
    for key, info in pipeline.list_available_models().items():
        print(f"  {key}: {info['repo_id']}")
        print(f"    Function calling: {info['supports_function_calling']}")
        print(f"    VRAM (4-bit): {info['vram_requirements_gb']['4bit']} GB")

    # Download and quantize Ministral-3-8B
    def progress(stage, pct):
        print(f"[{pct * 100:5.1f}%] {stage}")

    results = pipeline.download_and_quantize(
        model_key="ministral3-8b",
        quantize_4bit=True,
        quantize_2bit=False,
        progress_callback=progress,
    )

    print("\nResults:", results)
