"""Quantization operations for LLM worker."""

from typing import Dict

from airunner.enums import SignalCode


class QuantizationMixin:
    """Handles LLM quantization operations.

    This mixin provides functionality for:
    - Starting quantization requests
    - Updating quantization settings
    - Emitting quantization progress and completion

    Note: Modern approach uses bitsandbytes auto-quantization during
    model loading rather than creating separate disk files.
    """

    def on_llm_start_quantization_signal(self, data: dict) -> None:
        """Handle manual quantization request from UI.

        Unlike the old GPTQModel approach (which created separate files on disk),
        this now uses the same bitsandbytes auto-quantization that happens during
        model loading. This is the recommended approach as it:
        - Happens at load time (no separate disk files)
        - Works reliably across all model types
        - Uses less disk space

        Args:
            data: Contains bits for quantization level (2, 4, or 8)
        """
        bits = data.get("bits", 4)

        self.logger.info(
            f"Manual quantization requested: {bits}-bit "
            "(will apply during next model load)"
        )

        dtype_map = {
            2: "2bit",
            4: "4bit",
            8: "8bit",
        }

        if bits not in dtype_map:
            error_msg = (
                f"Invalid quantization level: {bits}. Must be 2, 4, or 8."
            )
            self.logger.error(error_msg)
            self.emit_signal(
                SignalCode.LLM_QUANTIZATION_FAILED,
                {"error": error_msg},
            )
            return

        self._update_quantization_settings(dtype_map[bits])
        self._emit_quantization_complete(bits)

    def _update_quantization_settings(self, dtype: str) -> None:
        """Update settings to use specified quantization level.

        Args:
            dtype: Data type string (2bit, 4bit, or 8bit)
        """
        # Import here to avoid circular dependency
        from airunner.settings import SETTINGS_MANAGER

        SETTINGS_MANAGER.llm_generator_settings.dtype = dtype
        SETTINGS_MANAGER.save_settings()

        self.logger.info(
            f"Quantization level set to {dtype}. "
            "This will take effect when the model is next loaded."
        )

    def _emit_quantization_complete(self, bits: int) -> None:
        """Emit quantization completion signal.

        Args:
            bits: Quantization bit level (2, 4, or 8)
        """
        self.emit_signal(
            SignalCode.LLM_QUANTIZATION_COMPLETE,
            {
                "bits": bits,
                "message": f"Quantization set to {bits}-bit "
                "(applies on next model load)",
            },
        )

    def _run_quantization(self, data: Dict) -> None:
        """Deprecated - kept for compatibility but no longer used.

        Quantization now happens automatically during model loading.

        Args:
            data: Quantization configuration (unused)
        """
