"""FLUX generation preparation mixin."""

from typing import Dict, Any
import torch


class FluxGenerationMixin:
    """Handles generation data preparation for FLUX models."""

    def _prepare_pipe_data(self) -> Dict[str, Any]:
        """Prepare pipeline initialization parameters with FLUX optimizations."""
        data = super()._prepare_pipe_data()

        data["torch_dtype"] = torch.bfloat16
        data.pop("safety_checker", None)
        data.pop("feature_extractor", None)

        is_gguf = self.model_path and str(self.model_path).lower().endswith(
            ".gguf"
        )

        if not is_gguf:
            quantization_config = self._get_quantization_config()
            if quantization_config:
                data["quantization_config"] = quantization_config
                self.logger.info("4-bit quantization enabled for FLUX model")
        else:
            self.logger.info(
                "GGUF model detected - skipping additional quantization"
            )

        return data

    def _load_prompt_embeds(self):
        """Load and prepare prompt embeddings for FLUX."""
        self._current_prompt = self.prompt
        self._current_negative_prompt = self.negative_prompt
        self.logger.debug("FLUX prompt handling (no pre-computed embeddings)")

    def _prepare_data(self, active_rect=None) -> Dict:
        """Prepare generation data for FLUX pipeline."""
        data = super()._prepare_data(active_rect)
        self._strip_flux_incompatible_params(data)
        self._enforce_flux_guidance(data)
        data["max_sequence_length"] = 512
        self._log_flux_generation_params(data)
        return data

    def _strip_flux_incompatible_params(self, data: Dict) -> None:
        """Remove parameters the FLUX pipeline cannot consume."""
        for key in ("clip_skip", "strength", "negative_prompt"):
            data.pop(key, None)

    def _enforce_flux_guidance(self, data: Dict) -> None:
        """Clamp guidance to the safe FLUX range."""
        guidance_scale = data.get("guidance_scale", 3.5)
        if guidance_scale <= 5.0:
            return

        self.logger.warning(
            "FLUX guidance_scale %.2f too high, clamping to 3.5. "
            "FLUX uses lower guidance than SD (recommended: 3.5 for dev, 0.0 for schnell)",
            guidance_scale,
        )
        data["guidance_scale"] = 3.5

    def _log_flux_generation_params(self, data: Dict) -> None:
        """Log core generation parameters for debugging."""
        debug_fields = {
            "prompt": data.get("prompt", "MISSING!"),
            "guidance_scale": data.get("guidance_scale", "MISSING!"),
            "steps": data.get("num_inference_steps", "MISSING!"),
            "size": f"{data.get('width')}x{data.get('height')}",
            "max_sequence_length": data.get("max_sequence_length", "MISSING!"),
        }
        self.logger.info(
            "[FLUX DEBUG] Keys: %s | Values: %s",
            list(data.keys()),
            debug_fields,
        )

    def _load_deep_cache(self):
        """Deep cache not supported for FLUX."""
        pass
