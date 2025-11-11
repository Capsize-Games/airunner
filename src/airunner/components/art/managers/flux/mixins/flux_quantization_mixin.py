"""FLUX quantization management mixin."""

from pathlib import Path
from typing import Any, Optional
import torch
from transformers import BitsAndBytesConfig

from airunner.enums import SignalCode


class FluxQuantizationMixin:
    """Handles all quantization-related operations for FLUX models."""

    def _get_quantization_config(self) -> Optional[BitsAndBytesConfig]:
        """Get 4-bit quantization configuration for FLUX models."""
        try:
            quantization_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_compute_dtype=torch.bfloat16,
                bnb_4bit_use_double_quant=True,
                bnb_4bit_quant_type="nf4",
            )
            return quantization_config
        except Exception as e:
            self.logger.warning(f"Could not create quantization config: {e}")
            self.logger.warning(
                "Install bitsandbytes for 4-bit quantization: pip install bitsandbytes"
            )
            return None

    def _get_quantized_model_path(self, model_path: str) -> Path:
        """Get path where quantized model should be saved."""
        base_path = Path(model_path)
        parent = base_path.parent
        name = base_path.name
        quantized_path = parent / f"{name}_4bit_quantized"
        return quantized_path

    def _quantized_model_exists(self, model_path: str) -> bool:
        """Check if quantized model already exists on disk."""
        quantized_path = self._get_quantized_model_path(model_path)
        if not quantized_path.exists():
            return False

        essential_files = ["config.json", "model_index.json"]
        for filename in essential_files:
            if not (quantized_path / filename).exists():
                return False

        model_files = list(quantized_path.glob("*.safetensors")) + list(
            quantized_path.glob("*.bin")
        )
        if not model_files:
            return False

        self.logger.info(f"Found existing quantized model at {quantized_path}")
        return True

    def _save_quantized_model(self, model_path: str) -> None:
        """Persist the quantized pipeline for faster future loads."""
        if self._should_skip_quantized_save(model_path):
            return
        self._persist_quantized_pipeline(
            self._get_quantized_model_path(model_path)
        )

    def _persist_quantized_pipeline(self, quantized_path: Path) -> None:
        """Save the pipeline and surface status updates."""
        try:
            self._announce_quantized_save(
                f"Saving quantized FLUX model to {quantized_path}"
            )
            quantized_path.mkdir(parents=True, exist_ok=True)
            self._pipe.save_pretrained(
                str(quantized_path), safe_serialization=True
            )
            self._announce_quantized_save(
                f"✓ Quantized model saved to {quantized_path}"
            )
        except Exception as exc:  # noqa: BLE001 - saving is optional
            # Meta tensor errors are expected for single-file quantized loads
            # and don't impact model functionality - just cache performance
            message = str(exc).lower()
            if "meta tensor" in message:
                self.logger.debug(
                    "Quantized pipeline save skipped due to meta tensors "
                    "(expected for single-file loads)"
                )
            else:
                self.logger.error(
                    "Failed to save quantized model at %s: %s",
                    quantized_path,
                    exc,
                )
                self._announce_quantized_save(
                    f"⚠ Failed to save quantized model: {exc}"
                )
            self._handle_quantized_save_failure(quantized_path, exc)

    def _should_skip_quantized_save(self, model_path: str) -> bool:
        """Return True if saving a quantized model is unnecessary."""
        if str(model_path).lower().endswith(".gguf"):
            self.logger.info(
                "Skipping save for GGUF model (already quantized)"
            )
            return True

        if self._pipe is not None:
            return False

        self.logger.error("Cannot save quantized model: pipeline is None")
        return True

    def _announce_quantized_save(self, message: str) -> None:
        """Log and emit a status message for quantized saves."""
        self.logger.info(message)
        self.emit_signal(SignalCode.UPDATE_DOWNLOAD_LOG, {"message": message})

    def _load_or_quantize_text_encoder(
        self,
        model_class: Any,
        source_dir: Path,
        cache_dir: Path,
        quantization_config: BitsAndBytesConfig,
    ) -> Any:
        """Load cached quantized text encoder or quantize and cache it."""
        cached_model = self._load_cached_encoder(
            model_class, cache_dir, quantization_config
        )
        if cached_model is not None:
            return cached_model

        model = self._quantize_encoder(
            model_class, source_dir, quantization_config
        )
        self._cache_quantized_encoder(model, cache_dir)
        return model

    def _load_cached_encoder(
        self,
        model_class: Any,
        cache_dir: Path,
        quantization_config: BitsAndBytesConfig,
    ) -> Optional[Any]:
        """Load a previously cached quantized encoder if available."""
        if not self._has_cached_encoder(cache_dir):
            return None

        try:
            return self._load_cached_encoder_from_disk(
                model_class, cache_dir, quantization_config
            )
        except Exception as exc:  # noqa: BLE001 - informational
            self._log_cached_encoder_failure(cache_dir, exc)
            return None

    @staticmethod
    def _has_cached_encoder(cache_dir: Path) -> bool:
        """Return True when a cached encoder with config exists."""
        return cache_dir.exists() and (cache_dir / "config.json").exists()

    def _load_cached_encoder_from_disk(
        self,
        model_class: Any,
        cache_dir: Path,
        quantization_config: BitsAndBytesConfig,
    ) -> Any:
        """Return cached encoder from disk."""
        self.logger.info("Loading cached quantized model from %s", cache_dir)
        return model_class.from_pretrained(
            str(cache_dir),
            quantization_config=quantization_config,
            device_map="auto",
            local_files_only=True,
        )

    def _log_cached_encoder_failure(
        self, cache_dir: Path, exc: Exception
    ) -> None:
        """Log cache load failure while keeping refactor readable."""
        self.logger.warning(
            "Failed to load cached model from %s: %s. Quantizing from source instead.",
            cache_dir,
            exc,
        )

    def _quantize_encoder(
        self,
        model_class: Any,
        source_dir: Path,
        quantization_config: BitsAndBytesConfig,
    ) -> Any:
        """Quantize an encoder from its source directory."""
        self.logger.info("Quantizing model from %s", source_dir)
        return model_class.from_pretrained(
            str(source_dir),
            quantization_config=quantization_config,
            device_map="auto",
            local_files_only=True,
        )

    def _cache_quantized_encoder(self, model: Any, cache_dir: Path) -> None:
        """Persist a quantized encoder for faster future loads."""
        try:
            cache_dir.parent.mkdir(parents=True, exist_ok=True)
            self.logger.info("Saving quantized model to %s", cache_dir)
            model.save_pretrained(str(cache_dir))
            self.logger.info(
                "✓ Quantized model cached for faster future loads"
            )
        except Exception as exc:  # noqa: BLE001 - cache failures are non-fatal
            self.logger.warning(
                "Failed to cache quantized model at %s: %s", cache_dir, exc
            )
