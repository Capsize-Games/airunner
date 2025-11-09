"""FLUX memory management mixin."""

from typing import Any

import torch


class FluxMemoryMixin:
    """Handles memory optimization for FLUX models."""

    def _make_memory_efficient(self):
        """Apply memory optimizations for low VRAM systems."""
        if self._pipe is None:
            return

        try:
            if torch.cuda.is_available():
                vram_gb = self._get_vram_gb()
                self._apply_vram_optimizations(vram_gb)
                self._enable_slicing_optimizations()
                self._set_memory_flags(vram_gb)
            else:
                self.logger.warning("CUDA not available, running on CPU")
        except Exception as e:
            if e is not None:
                self.logger.warning(
                    f"Could not apply all memory optimizations: {e}"
                )
            else:
                self.logger.debug("Memory optimizations applied with warnings")

    def _get_vram_gb(self) -> float:
        """Get available VRAM in GB."""
        total_vram = torch.cuda.get_device_properties(0).total_memory
        return total_vram / (1024**3)

    def _apply_vram_optimizations(self, vram_gb: float):
        """Apply memory optimizations for GGUF FLUX models."""
        self.logger.info(f"Detected {vram_gb:.1f}GB VRAM")

        if vram_gb < 24:
            self.logger.info("Enabling model CPU offload for GGUF")
            self._pipe.enable_model_cpu_offload()
        else:
            self.logger.info("Loading full model to GPU")
            self._pipe.to(self._device)

        self._force_vae_fp32()

    def _enable_slicing_optimizations(self):
        """Enable VAE tiling, slicing, and attention slicing for memory efficiency."""
        if hasattr(self._pipe, "enable_vae_tiling"):
            self._pipe.enable_vae_tiling()
            self.logger.debug("VAE tiling enabled")

        if hasattr(self._pipe, "enable_vae_slicing"):
            self._pipe.enable_vae_slicing()
            self.logger.debug("VAE slicing enabled")

        if hasattr(self._pipe, "enable_attention_slicing"):
            self._pipe.enable_attention_slicing("auto")
            self.logger.debug("Attention slicing enabled")

    def _set_memory_flags(self, vram_gb: float):
        """Set memory optimization flags."""
        self._memory_settings_flags["cpu_offload_applied"] = vram_gb < 24
        self._memory_settings_flags["sequential_cpu_offload"] = vram_gb < 16
        self._memory_settings_flags["vae_tiling"] = True
        self._memory_settings_flags["vae_slicing"] = True
        self._memory_settings_flags["attention_slicing"] = True

    def _force_vae_fp32(self) -> None:
        """Force the VAE (weights and decode path) to run in float32."""

        if self._pipe is None:
            return

        vae = getattr(self._pipe, "vae", None)
        if vae is None:
            return

        try:
            vae.float()  # type: ignore[call-arg]
        except Exception:  # noqa: BLE001 - fall back to manual casting
            for module in vae.modules():
                for name, parameter in list(module._parameters.items()):
                    if (
                        parameter is not None
                        and parameter.dtype != torch.float32
                    ):
                        module._parameters[name] = parameter.to(torch.float32)
                for name, buffer in list(module._buffers.items()):
                    if buffer is not None and buffer.dtype == torch.bfloat16:
                        module._buffers[name] = buffer.to(torch.float32)

        if hasattr(vae, "config"):
            setattr(vae.config, "force_upcast", True)

        self._wrap_vae_decode_with_upcast(vae)

    def _wrap_vae_decode_with_upcast(self, vae: Any) -> None:
        """Wrap the VAE decode to ensure float32 decode without autocast."""

        if getattr(vae, "_flux_decode_wrapped", False):
            return

        original_decode = vae.decode

        def _decode_with_upcast(latents, *args, **kwargs):
            try:
                vae.float()
            except Exception:  # noqa: BLE001 - best effort
                pass

            latents = latents.to(torch.float32)
            device_type = latents.device.type
            if device_type in {"cuda", "xpu"}:
                with torch.autocast(device_type=device_type, enabled=False):
                    return original_decode(latents, *args, **kwargs)
            return original_decode(latents, *args, **kwargs)

        vae.decode = _decode_with_upcast  # type: ignore[assignment]
        vae._flux_decode_wrapped = True  # type: ignore[attr-defined]
        if not getattr(self, "_flux_vae_fp32_logged", False):
            self.logger.info(
                "✓ Upcast VAE to float32 and wrapped decode for FLUX"
            )
            self._flux_vae_fp32_logged = True

    def _clear_memory_efficient_settings(self):
        """Clear memory optimization flags and disable optimizations."""
        if self._pipe is not None:
            try:
                if hasattr(self._pipe, "disable_vae_tiling"):
                    self._pipe.disable_vae_tiling()
                if hasattr(self._pipe, "disable_vae_slicing"):
                    self._pipe.disable_vae_slicing()
                if hasattr(self._pipe, "disable_attention_slicing"):
                    self._pipe.disable_attention_slicing()
            except Exception as e:
                self.logger.debug(f"Error clearing memory settings: {e}")

        super()._clear_memory_efficient_settings()
