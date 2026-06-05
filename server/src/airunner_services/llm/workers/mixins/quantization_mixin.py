"""Service-owned quantization operations for the LLM worker."""

from typing import Dict
from airunner_services.utils.application.enum_resolver import signal_code_proxy

SignalCode = signal_code_proxy(
    {
        "LLM_QUANTIZATION_COMPLETE": "llm_quantization_complete",
        "LLM_QUANTIZATION_FAILED": "llm_quantization_failed",
    }
)


class QuantizationMixin:
    """Handle LLM quantization requests for the worker."""

    def on_llm_start_quantization_signal(self, data: dict) -> None:
        """Persist one requested quantization level for the next model load."""
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

        try:
            self._update_quantization_settings(dtype_map[bits])
        except Exception as exc:
            error_msg = f"Failed to update quantization settings: {exc}"
            self.logger.error(error_msg)
            self.emit_signal(
                SignalCode.LLM_QUANTIZATION_FAILED,
                {"error": error_msg},
            )
            return

        self._emit_quantization_complete(bits)

    def _update_quantization_settings(self, dtype: str) -> None:
        """Update the persisted LLM dtype setting when available."""
        settings = getattr(self, "llm_generator_settings", None)
        if settings is None:
            raise RuntimeError("LLM generator settings are unavailable")

        settings.dtype = dtype

        save = getattr(settings, "save", None)
        if callable(save):
            save()

        notify = getattr(self, "_notify_setting_updated", None)
        if callable(notify):
            notify(None, None, None)

        self.logger.info(
            f"Quantization level set to {dtype}. "
            "This will take effect when the model is next loaded."
        )

    def _emit_quantization_complete(self, bits: int) -> None:
        """Emit the standard quantization completion signal."""
        self.emit_signal(
            SignalCode.LLM_QUANTIZATION_COMPLETE,
            {
                "bits": bits,
                "message": (
                    f"Quantization set to {bits}-bit "
                    "(applies on next model load)"
                ),
            },
        )

    def _run_quantization(self, data: Dict) -> None:
        """Keep the deprecated entry point for compatibility."""
        return None


__all__ = ["QuantizationMixin"]
