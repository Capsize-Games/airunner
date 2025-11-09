"""FLUX pipeline loading mixin."""

import os
from pathlib import Path
from typing import Any, Dict, Optional

from airunner.enums import SignalCode
from airunner.settings import (
    AIRUNNER_ADD_WATER_MARK,
    AIRUNNER_LOCAL_FILES_ONLY,
)


class FluxPipelineLoadingMixin:
    """Handles pipeline loading operations for FLUX models."""

    def _load_pipeline_from_cache(
        self,
        pipeline_class: Any,
        model_path: str,
        data: Dict[str, Any],
    ) -> bool:
        """Try loading a quantized pipeline from disk cache."""
        if not self._quantized_model_exists(model_path):
            return False

        quantized_path = self._get_quantized_model_path(model_path)
        try:
            self._pipe = pipeline_class.from_pretrained(
                str(quantized_path), **data
            )
        except Exception as exc:
            self.logger.warning(
                "Failed to load quantized model from disk: %s", exc
            )
            return False

        self.logger.info("✓ Loaded quantized model from disk")
        self._force_vae_fp32()
        return True

    def _load_pipeline_by_type(
        self,
        model_path: str,
        pipeline_class: Any,
        config_path: str,
        data: Dict[str, Any],
    ) -> None:
        """Dispatch pipeline loading based on model file layout."""
        if str(model_path).lower().endswith(".gguf"):
            self._load_gguf_model(model_path, pipeline_class)
            return

        if self.use_from_single_file:
            self._load_single_file_model(
                model_path, pipeline_class, config_path, data
            )
            return

        self._load_pretrained_model(
            model_path, pipeline_class, config_path, data
        )

    def _load_single_file_model(
        self,
        model_path: Path,
        pipeline_class: Any,
        config_path: Optional[str],
        data: Dict,
    ) -> None:
        """Load FLUX model from single file with quantization."""
        self._announce_single_file_load(model_path)
        kwargs = self._single_file_kwargs(data, config_path)
        self._pipe = pipeline_class.from_single_file(str(model_path), **kwargs)
        self.logger.info("✓ Model loaded with 4-bit quantization")

    def _announce_single_file_load(self, model_path: Path) -> None:
        """Emit consistent logs when loading single-file models."""
        message = "Loading FLUX model with 4-bit quantization..."
        self.logger.info("%s %s", message, model_path)
        self.emit_signal(
            SignalCode.UPDATE_DOWNLOAD_LOG,
            {"message": message},
        )

    def _single_file_kwargs(
        self, data: Dict, config_path: Optional[str]
    ) -> Dict:
        """Build kwargs for single-file FLUX loading."""
        kwargs = {
            "add_watermarker": AIRUNNER_ADD_WATER_MARK,
            "local_files_only": AIRUNNER_LOCAL_FILES_ONLY,
            **data,
        }
        if config_path:
            kwargs["config"] = str(config_path)
        return kwargs

    def _load_pretrained_model(
        self,
        model_path: Path,
        pipeline_class: Any,
        config_path: Optional[str],
        data: Dict,
    ) -> None:
        """Load FLUX model from pretrained directory."""
        kwargs = {**data}
        if config_path:
            kwargs["config"] = str(config_path)

        file_directory = (
            os.path.dirname(model_path)
            if os.path.isfile(model_path)
            else model_path
        )
        self._pipe = pipeline_class.from_pretrained(
            str(file_directory), **kwargs
        )

    def _set_pipe(self, config_path: str, data: Dict):
        """Load FLUX pipeline with automatic quantization."""
        pipeline_class = self._pipeline_class
        model_path = self.model_path

        if self._load_pipeline_from_cache(pipeline_class, model_path, data):
            return

        try:
            self._load_pipeline_by_type(
                model_path, pipeline_class, config_path, data
            )
        except Exception as exc:
            self.logger.error("Failed to load FLUX model: %s", exc)
            raise

        self._force_vae_fp32()

        if not str(model_path).lower().endswith(".gguf"):
            self._save_quantized_model(model_path)
