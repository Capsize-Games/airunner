"""FLUX memory management mixin."""

import gc
from contextlib import contextmanager
from typing import Any, Generator

import torch

try:
    from diffusers.hooks import apply_group_offloading
    HAS_GROUP_OFFLOADING = True
except ImportError:
    apply_group_offloading = None
    HAS_GROUP_OFFLOADING = False


class FluxMemoryMixin:
    """Handles memory optimization for FLUX models."""

    @staticmethod
    @contextmanager
    def memory_optimized_loading() -> Generator[None, None, None]:
        """Context manager for memory-optimized model loading.
        
        Clears GPU memory before and after loading to minimize VRAM spikes.
        Use this around heavy model loading operations.
        
        Usage:
            with self.memory_optimized_loading():
                model = Model.from_pretrained(...)
        """
        # Clear before loading
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.synchronize()
        
        try:
            yield
        finally:
            # Clear after loading to release any temporary allocations
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                torch.cuda.synchronize()

    @staticmethod
    def clear_gpu_memory() -> None:
        """Aggressively clear GPU memory.
        
        Call this between loading stages to minimize peak VRAM usage.
        """
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.synchronize()
        gc.collect()  # Second pass for released references

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
        """Apply memory optimizations for FLUX models.
        
        Strategy for 16GB cards with quantized models:
        - Keep transformer on GPU (largest, most frequently used)
        - Keep T5 on CPU, move to GPU only during prompt encoding
        - This avoids accelerate hooks which cause RAM leaks
        """
        self.logger.info(f"Detected {vram_gb:.1f}GB VRAM")
        
        # Move T5 to CPU to free VRAM for inference
        # It will be moved to GPU temporarily during prompt encoding
        text_encoder_2 = getattr(self._pipe, "text_encoder_2", None)
        if text_encoder_2 is not None:
            try:
                # For quantized models, we need to be careful
                # Just move it to CPU - the pipeline will handle it
                text_encoder_2.to("cpu")
                self.logger.info("Moved T5 encoder to CPU (will move to GPU during prompt encoding)")
            except Exception as e:
                self.logger.warning(f"Could not move T5 to CPU: {e}")
        
        # Keep other models on GPU
        self._ensure_models_on_gpu()
        
        self._force_vae_fp32()

    def _check_if_quantized(self) -> bool:
        """Check if any pipeline models are quantized with BitsAndBytes."""
        for component_name in ["transformer", "text_encoder_2"]:
            component = getattr(self._pipe, component_name, None)
            if component is not None:
                # Check for quantization config
                if hasattr(component, "config"):
                    config = component.config
                    if hasattr(config, "quantization_config"):
                        return True
                # Check for BitsAndBytes linear layers
                if hasattr(component, "modules"):
                    for module in component.modules():
                        module_class = module.__class__.__name__
                        if "Linear4bit" in module_class or "Linear8bitLt" in module_class:
                            return True
        return False

    def _ensure_models_on_gpu(self):
        """Ensure VAE, CLIP, and transformer are on GPU.
        
        Note: T5 (text_encoder_2) is intentionally kept on CPU to save VRAM.
        """
        device = torch.device("cuda:0")
        
        # Move VAE and CLIP to GPU
        for component_name in ["vae", "text_encoder"]:
            component = getattr(self._pipe, component_name, None)
            if component is not None:
                try:
                    component.to(device)
                    self.logger.debug(f"Moved {component_name} to GPU")
                except Exception as e:
                    self.logger.debug(f"Could not move {component_name}: {e}")
        
        # Verify transformer is on GPU (should be from loading)
        transformer = getattr(self._pipe, "transformer", None)
        if transformer is not None:
            try:
                first_param = next(transformer.parameters(), None)
                if first_param is not None:
                    self.logger.debug(f"transformer on device: {first_param.device}")
            except Exception:
                pass

    def _apply_group_offloading(self, vram_gb: float):
        """Apply group offloading to pipeline components.
        
        Group offloading moves layers between CPU/GPU during inference without
        the memory leaks associated with accelerate hooks on quantized models.
        """
        # Determine offload settings based on VRAM
        # Use CUDA streams for async transfers when VRAM allows
        use_stream = vram_gb >= 12
        offload_type = "leaf_level"  # Most memory efficient
        onload_device = torch.device("cuda:0")
        offload_device = torch.device("cpu")
        
        self.logger.info(
            f"Applying group offloading (type={offload_type}, stream={use_stream})"
        )
        
        # Apply to transformer (largest component)
        transformer = getattr(self._pipe, "transformer", None)
        if transformer is not None:
            try:
                apply_group_offloading(
                    transformer,
                    onload_device=onload_device,
                    offload_device=offload_device,
                    offload_type=offload_type,
                    use_stream=use_stream,
                )
                self.logger.info("✓ Group offloading applied to transformer")
            except Exception as e:
                self.logger.warning(f"Could not apply group offloading to transformer: {e}")
        
        # Apply to T5 text encoder (second largest)
        text_encoder_2 = getattr(self._pipe, "text_encoder_2", None)
        if text_encoder_2 is not None:
            try:
                apply_group_offloading(
                    text_encoder_2,
                    onload_device=onload_device,
                    offload_device=offload_device,
                    offload_type=offload_type,
                    use_stream=use_stream,
                )
                self.logger.info("✓ Group offloading applied to text_encoder_2")
            except Exception as e:
                self.logger.warning(f"Could not apply group offloading to text_encoder_2: {e}")
        
        # Apply to VAE (for decode step)
        vae = getattr(self._pipe, "vae", None)
        if vae is not None:
            try:
                apply_group_offloading(
                    vae,
                    onload_device=onload_device,
                    offload_device=offload_device,
                    offload_type=offload_type,
                    use_stream=use_stream,
                )
                self.logger.info("✓ Group offloading applied to VAE")
            except Exception as e:
                self.logger.warning(f"Could not apply group offloading to VAE: {e}")

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
