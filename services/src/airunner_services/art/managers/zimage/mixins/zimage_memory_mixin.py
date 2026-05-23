"""Z-Image memory management mixin."""

import gc
from contextlib import contextmanager
from typing import Generator

import torch
from bitsandbytes.nn import Linear8bitLt, Linear4bit  # type: ignore


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
        """Get total VRAM in GB."""
        total_vram = torch.cuda.get_device_properties(0).total_memory
        return total_vram / (1024**3)

    def _is_quantized(self) -> bool:
        """Check if the model is using quantization (4-bit or 8-bit).
        
        Returns:
            True if the model is quantized, False otherwise.
        """
        # Check text encoder for quantization
        text_encoder = getattr(self._pipe, "text_encoder", None)
        if text_encoder is not None:
            # Check for HF quantizer (used by both 4-bit and 8-bit)
            if hasattr(text_encoder, "hf_quantizer") and text_encoder.hf_quantizer is not None:
                return True
            # Check for quantization_config attribute
            if hasattr(text_encoder, "config") and hasattr(text_encoder.config, "quantization_config"):
                return True
            # Check for BitsAndBytes linear layers (8-bit uses these)
            if Linear8bitLt is not None and Linear4bit is not None:
                for module in text_encoder.modules():
                    if isinstance(module, (Linear8bitLt, Linear4bit)):
                        return True
        
        # Check transformer for quantization
        transformer = getattr(self._pipe, "transformer", None)
        if transformer is not None:
            if hasattr(transformer, "hf_quantizer") and transformer.hf_quantizer is not None:
                return True
            if Linear8bitLt is not None and Linear4bit is not None:
                for module in transformer.modules():
                    if isinstance(module, (Linear8bitLt, Linear4bit)):
                        return True
        
        return False

    def _apply_vram_optimizations(self, vram_gb: float):
        """Apply memory optimizations for Z-Image models.
        
        Memory usage varies by quantization level:
        - 4-bit: Transformer ~1.4GB, Text Encoder ~2.4GB, Total ~4GB
        - 8-bit: Transformer ~3GB, Text Encoder ~4GB, Total ~7-8GB
        - Full precision (bf16): Transformer ~5.7GB, Text Encoder ~8GB, Total ~14GB
        
        For 16GB cards with 8-bit models, VAE tiling is critical to avoid OOM
        during decode, which can spike memory by ~2-3GB.
        """
        self.logger.info(f"Detected {vram_gb:.1f}GB total VRAM")
        
        is_quantized = self._is_quantized()
        
        if is_quantized:
            self.logger.info("Using quantized models - applying memory optimizations")
            # Quantized models handle device placement via device_map='auto'
            # Just move VAE to GPU since it's not quantized
            self._move_vae_to_gpu()
            
            # For cards with <= 16GB VRAM, keep VAE in float16 instead of float32
            # to save ~200MB and reduce decode memory spikes
            if vram_gb <= 18:
                self._optimize_vae_for_low_vram()
            else:
                self._force_vae_fp32()
        elif vram_gb < 24:
            # Non-quantized: Enable CPU offload for low VRAM systems
            try:
                self._pipe.enable_model_cpu_offload()
                self.logger.info("Enabled model CPU offload for Z-Image")
            except Exception as e:
                self.logger.warning(f"Could not enable CPU offload: {e}")
            # Keep VAE in fp16/bf16 for low VRAM
            self._optimize_vae_for_low_vram()
        else:
            # Non-quantized high VRAM: Move everything to GPU
            self._ensure_models_on_gpu()
            self._force_vae_fp32()

    def _move_vae_to_gpu(self):
        """Move VAE to GPU (for use with quantized models).
        
        Note: For native FP8 pipelines, VAE is kept on CPU and moved
        dynamically during decode to conserve VRAM.
        """
        # Check if using native FP8 pipeline - skip VAE move
        if hasattr(self._pipe, "is_native_fp8") and self._pipe.is_native_fp8:
            self.logger.debug("Native FP8 pipeline: keeping VAE on CPU (dynamic placement during decode)")
            return
        
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
        Only use this when VRAM is plentiful (>18GB).
        """
        vae = getattr(self._pipe, "vae", None)
        if vae is not None:
            try:
                if hasattr(vae, "dtype") and vae.dtype == torch.bfloat16:
                    vae.to(torch.float32)
                    self.logger.debug("Converted VAE to float32 for better quality")
            except Exception as e:
                self.logger.debug(f"Could not convert VAE to float32: {e}")

    def _optimize_vae_for_low_vram(self):
        """Keep VAE in float16 for lower memory usage.
        
        For VRAM-constrained systems, keeping VAE in float16/bfloat16
        saves ~200MB and reduces memory spikes during decode.
        """
        vae = getattr(self._pipe, "vae", None)
        if vae is not None:
            try:
                # If VAE is in float32, convert to float16 to save memory
                if hasattr(vae, "dtype") and vae.dtype == torch.float32:
                    vae.to(torch.float16)
                    self.logger.debug("Converted VAE to float16 for lower VRAM usage")
                else:
                    self.logger.debug(f"VAE dtype: {getattr(vae, 'dtype', 'unknown')}")
            except Exception as e:
                self.logger.debug(f"Could not optimize VAE for low VRAM: {e}")

    def _enable_slicing_optimizations(self):
        """Enable VAE slicing optimizations for lower VRAM usage.
        
        VAE slicing and tiling reduce peak memory during decode by processing
        the image in smaller chunks. This is critical for avoiding OOM on
        16GB cards when using 8-bit quantization.
        """
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
        self._memory_settings_flags["is_quantized"] = self._is_quantized()
