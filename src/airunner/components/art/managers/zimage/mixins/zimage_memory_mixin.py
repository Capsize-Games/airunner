"""Z-Image memory management mixin."""

import gc
from contextlib import contextmanager
from typing import Generator

import torch


class ZImageMemoryMixin:
    """Handles memory optimization for Z-Image models."""

    @staticmethod
    @contextmanager
    def memory_optimized_loading() -> Generator[None, None, None]:
        """Context manager for memory-optimized model loading.
        
        Clears GPU memory before and after loading to minimize VRAM spikes.
        """
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.synchronize()
        
        try:
            yield
        finally:
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                torch.cuda.synchronize()

    @staticmethod
    def clear_gpu_memory() -> None:
        """Aggressively clear GPU memory."""
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.synchronize()
        gc.collect()

    def _make_memory_efficient(self):
        """Apply memory optimizations for low VRAM systems.
        
        Z-Image has a ~6B parameter transformer and ~8GB text encoder (Qwen).
        Total model size is ~32GB unquantized, so memory optimization is critical.
        """
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
        """Apply memory optimizations for Z-Image models.
        
        With 4-bit quantization, the model is much smaller:
        - Transformer: ~1.4GB (was ~5.7GB)
        - Text Encoder: ~2.4GB (was ~8GB)
        - VAE: ~0.16GB
        - Total: ~4GB (was ~14GB)
        
        CPU offload is generally not needed with quantization, and can cause
        issues with quantized models.
        """
        self.logger.info(f"Detected {vram_gb:.1f}GB VRAM")
        
        # Check if models are quantized (4-bit models use device_map='auto')
        text_encoder = getattr(self._pipe, "text_encoder", None)
        is_quantized = (
            text_encoder is not None 
            and hasattr(text_encoder, "hf_quantizer") 
            and text_encoder.hf_quantizer is not None
        )
        
        if is_quantized:
            self.logger.info("Using 4-bit quantized models (~4GB total)")
            # Quantized models already handle device placement via device_map='auto'
            # Just move VAE to GPU since it's not quantized
            self._move_vae_to_gpu()
        elif vram_gb < 24:
            # Non-quantized: Enable CPU offload for low VRAM systems
            try:
                self._pipe.enable_model_cpu_offload()
                self.logger.info("Enabled model CPU offload for Z-Image")
            except Exception as e:
                self.logger.warning(f"Could not enable CPU offload: {e}")
        else:
            # Non-quantized high VRAM: Move everything to GPU
            self._ensure_models_on_gpu()
        
        self._force_vae_fp32()

    def _move_vae_to_gpu(self):
        """Move VAE to GPU (for use with quantized models)."""
        vae = getattr(self._pipe, "vae", None)
        if vae is not None:
            try:
                vae.to("cuda:0")
                self.logger.debug("Moved VAE to GPU")
            except Exception as e:
                self.logger.debug(f"Could not move VAE to GPU: {e}")

    def _ensure_models_on_gpu(self):
        """Ensure all models are on GPU for high VRAM systems."""
        device = torch.device("cuda:0")
        
        for component_name in ["vae", "text_encoder", "transformer"]:
            component = getattr(self._pipe, component_name, None)
            if component is not None:
                try:
                    component.to(device)
                    self.logger.debug(f"Moved {component_name} to GPU")
                except Exception as e:
                    self.logger.debug(f"Could not move {component_name}: {e}")

    def _force_vae_fp32(self):
        """Force VAE to use float32 for better image quality.
        
        The VAE can produce artifacts in bfloat16, especially for complex images.
        """
        vae = getattr(self._pipe, "vae", None)
        if vae is not None:
            try:
                # Check if VAE is using bfloat16 and convert to float32
                if hasattr(vae, "dtype") and vae.dtype == torch.bfloat16:
                    vae.to(torch.float32)
                    self.logger.debug("Converted VAE to float32 for better quality")
            except Exception as e:
                self.logger.debug(f"Could not convert VAE to float32: {e}")

    def _enable_slicing_optimizations(self):
        """Enable VAE slicing optimizations for lower VRAM usage."""
        try:
            if hasattr(self._pipe, "enable_vae_slicing"):
                self._pipe.enable_vae_slicing()
                self.logger.debug("Enabled VAE slicing")
        except Exception as e:
            self.logger.debug(f"Could not enable VAE slicing: {e}")
        
        try:
            if hasattr(self._pipe, "enable_vae_tiling"):
                self._pipe.enable_vae_tiling()
                self.logger.debug("Enabled VAE tiling")
        except Exception as e:
            self.logger.debug(f"Could not enable VAE tiling: {e}")

    def _set_memory_flags(self, vram_gb: float):
        """Set memory optimization flags based on VRAM size."""
        self._memory_settings_flags["vram_gb"] = vram_gb
        self._memory_settings_flags["cpu_offload_applied"] = vram_gb < 24
