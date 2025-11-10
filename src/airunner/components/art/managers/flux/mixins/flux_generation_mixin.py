"""FLUX generation preparation mixin."""

from typing import Dict, Any
import torch
from airunner.components.application.exceptions import (
    InterruptedException,
)
from airunner.utils.memory import clear_memory


class FluxGenerationMixin:
    """Handles generation data preparation for FLUX models."""

    def _prepare_pipe_data(self) -> Dict[str, Any]:
        """Prepare pipeline initialization parameters with FLUX optimizations."""
        data = super()._prepare_pipe_data()

        data["torch_dtype"] = torch.bfloat16

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

    def _unload_pipe(self):
        """
        FLUX-specific pipeline unload.

        CRITICAL: FLUX uses 'transformer' not 'unet', so we must explicitly
        delete it. The base class only deletes unet/vae/text_encoder.
        """
        self.logger.info("=== FLUX _unload_pipe CALLED ===")
        self.logger.debug("Unloading FLUX pipe")
        if self._pipe is not None:
            # CRITICAL: Remove Accelerate hooks first to prevent CPU cache retention
            try:
                if hasattr(self._pipe, "_all_hooks"):
                    self.logger.debug("Removing Accelerate hooks")
                    for hook in self._pipe._all_hooks:
                        hook.remove()
                    self._pipe._all_hooks.clear()

                # Also check for model cpu offload hooks
                for component_name in [
                    "transformer",
                    "vae",
                    "text_encoder",
                    "text_encoder_2",
                    "scheduler",
                ]:
                    component = getattr(self._pipe, component_name, None)
                    if component is not None and hasattr(
                        component, "_hf_hook"
                    ):
                        self.logger.debug(
                            f"Removing hook from {component_name}"
                        )
                        if hasattr(component._hf_hook, "offload"):
                            component._hf_hook.offload(component)
                        delattr(component, "_hf_hook")

                    if component is not None and hasattr(
                        self._pipe, component_name
                    ):
                        print("Deleting component:", component_name)
                        delattr(self._pipe, component_name)
                        setattr(self._pipe, component_name, None)
            except Exception as e:
                self.logger.debug(f"Error removing Accelerate hooks: {e}")

            # Delete the pipeline itself
            del self._pipe
            self._pipe = None

            clear_memory()

            self.logger.info("✓ FLUX pipeline unloaded and memory freed")

    def _generate(self):
        """
        Override to add aggressive cleanup after FLUX generation completes.

        CRITICAL: FLUX decode buffers (~8-10GB) stay in memory after generation.
        We must explicitly free them after all image processing is done.
        """
        try:
            # Call parent implementation
            super()._generate()
        finally:
            # CRITICAL: Clean up after ALL image processing is complete
            # This happens after images are sent to canvas and export worker
            clear_memory()

            self.logger.debug("[FLUX CLEANUP] Memory freed")

    def _get_results(self, data):
        """
        Run pipeline inference with cleanup between generations.

        CRITICAL: FLUX GGUF models accumulate memory without cleanup.
        After each generation, we must explicitly free VAE decode buffers.
        """
        with torch.no_grad(), torch.amp.autocast(
            "cuda", dtype=torch.bfloat16, enabled=True
        ):
            total = 0
            while total < self.image_request.n_samples:
                if self.do_interrupt_image_generation:
                    raise InterruptedException()

                # Generate
                results = self._pipe(**data)
                yield results

                if not self.image_request.generate_infinite_images:
                    total += 1
