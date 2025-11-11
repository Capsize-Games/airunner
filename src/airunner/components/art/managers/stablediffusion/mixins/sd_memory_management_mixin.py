"""
Mixin providing memory optimization for Stable Diffusion models.

This mixin handles all memory efficiency settings including VAE slicing,
attention slicing, CPU offload, ToMe SD, and other VRAM optimizations.
"""

import torch
import tomesd
from diffusers.models.attention_processor import (
    AttnProcessor,
    AttnProcessor2_0,
)

from airunner.settings import (
    AIRUNNER_MEM_USE_LAST_CHANNELS,
    AIRUNNER_MEM_USE_ENABLE_VAE_SLICING,
    AIRUNNER_MEM_USE_ATTENTION_SLICING,
    AIRUNNER_MEM_USE_TILED_VAE,
    AIRUNNER_MEM_USE_ACCELERATED_TRANSFORMERS,
    AIRUNNER_MEM_USE_ENABLE_SEQUENTIAL_CPU_OFFLOAD,
    AIRUNNER_MEM_ENABLE_MODEL_CPU_OFFLOAD,
    AIRUNNER_MEM_USE_TOME_SD,
    AIRUNNER_MEM_TOME_SD_RATIO,
    AIRUNNER_DISABLE_FLASH_ATTENTION,
)
from airunner.utils.memory import is_ampere_or_newer
from airunner.utils.settings import get_qsettings


class SDMemoryManagementMixin:
    """Mixin providing memory optimization for Stable Diffusion models."""

    def _make_memory_efficient(self):
        """
        Apply all memory efficiency settings to pipeline.

        Applies settings like VAE slicing, attention slicing, CPU offload,
        ToMe SD, xformers, and torch.compile based on current memory settings.
        """
        self._current_memory_settings = self.memory_settings.to_dict()
        if not self._pipe:
            self.logger.error("Pipe is None, unable to apply memory settings")
            return

        # Apply all memory efficient settings using the helper method
        self._apply_memory_setting(
            "last_channels_applied",
            "use_last_channels",
            self._apply_last_channels,
        )
        self._apply_memory_setting(
            "vae_slicing_applied",
            "use_enable_vae_slicing",
            self._apply_vae_slicing,
        )
        self._apply_memory_setting(
            "attention_slicing_applied",
            "use_attention_slicing",
            self._apply_attention_slicing,
        )
        self._apply_memory_setting(
            "tiled_vae_applied", "use_tiled_vae", self._apply_tiled_vae
        )
        self._apply_memory_setting(
            "accelerated_transformers_applied",
            "use_accelerated_transformers",
            self._apply_accelerated_transformers,
        )

        # Apply xformers for Flash Attention 2 (major speedup)
        self._apply_xformers()

        # Apply torch.compile for 2-3x speedup (one-time compilation)
        self._apply_torch_compile()

        self._apply_memory_setting(
            "cpu_offload_applied",
            "use_enable_sequential_cpu_offload",
            self._apply_cpu_offload,
        )
        self._apply_memory_setting(
            "model_cpu_offload_applied",
            "enable_model_cpu_offload",
            self._apply_model_offload,
        )
        self._apply_memory_setting(
            "tome_sd_applied", "use_tome_sd", self._apply_tome
        )

    def _apply_memory_setting(self, setting_name, attribute_name, apply_func):
        """
        Apply individual memory setting if changed.

        Args:
            setting_name: Name of flag tracking application state.
            attribute_name: Name of setting attribute.
            apply_func: Function to call to apply the setting.
        """
        attr_val = getattr(self.memory_settings, attribute_name)
        if self._memory_settings_flags[setting_name] != attr_val:
            apply_func(attr_val)
            self._memory_settings_flags[setting_name] = attr_val

    def _apply_last_channels(self, attr_val):
        """
        Apply channels_last memory format to UNet.

        Args:
            attr_val: Whether to enable channels_last format.

        Channels-last improves memory access patterns on some GPUs.
        """
        enabled = AIRUNNER_MEM_USE_LAST_CHANNELS
        if enabled is None:
            enabled = attr_val
        self.logger.debug(
            f"{'Enabling' if enabled else 'Disabling'} torch.channels_last"
        )
        self._pipe.unet.to(
            memory_format=(
                torch.channels_last if enabled else torch.contiguous_format
            )
        )

    def _apply_vae_slicing(self, attr_val):
        """
        Apply VAE slicing for reduced VRAM usage.

        Args:
            attr_val: Whether to enable VAE slicing.

        VAE slicing processes images in smaller tiles to reduce memory.
        """
        enabled = AIRUNNER_MEM_USE_ENABLE_VAE_SLICING
        if enabled is None:
            enabled = attr_val
        try:
            if enabled:
                self.logger.debug("Enabling vae slicing")
                self._pipe.enable_vae_slicing()
            else:
                self.logger.debug("Disabling vae slicing")
                self._pipe.disable_vae_slicing()
        except AttributeError as e:
            self.logger.error("Failed to apply vae slicing")
            self.logger.error(e)

    def _apply_attention_slicing(self, attr_val):
        """
        Apply attention slicing for reduced VRAM usage.

        Args:
            attr_val: Whether to enable attention slicing.

        Attention slicing processes attention in smaller chunks.
        """
        enabled = AIRUNNER_MEM_USE_ATTENTION_SLICING
        if enabled is None:
            enabled = attr_val
        try:
            if attr_val:
                self.logger.debug("Enabling attention slicing")
                self._pipe.enable_attention_slicing(1)
            else:
                self.logger.debug("Disabling attention slicing")
                self._pipe.disable_attention_slicing()
        except AttributeError as e:
            self.logger.warning(f"Failed to apply attention slicing: {e}")

    def _apply_tiled_vae(self, attr_val):
        """
        Apply tiled VAE for very large images.

        Args:
            attr_val: Whether to enable tiled VAE.

        Tiled VAE processes large images in overlapping tiles.
        """
        enabled = AIRUNNER_MEM_USE_TILED_VAE
        if enabled is None:
            enabled = attr_val
        try:
            if enabled:
                self.logger.debug("Enabling tiled vae")
                self._pipe.vae.enable_tiling()
            else:
                self.logger.debug("Disabling tiled vae")
                self._pipe.vae.disable_tiling()
        except AttributeError:
            self.logger.warning("Tiled vae not supported for this model")

    def _apply_accelerated_transformers(self, attr_val):
        """
        Apply accelerated transformers (attention processor 2.0).

        Args:
            attr_val: Whether to enable accelerated transformers.

        Uses optimized attention on Ampere+ GPUs (RTX 30xx/40xx).
        """
        enabled = AIRUNNER_MEM_USE_ACCELERATED_TRANSFORMERS
        if enabled is None:
            enabled = attr_val

        if not is_ampere_or_newer(self._device_index):
            enabled = False

        self.logger.debug(
            f"{'Enabling' if enabled else 'Disabling'} accelerated transformers"
        )
        self._pipe.unet.set_attn_processor(
            AttnProcessor2_0() if enabled else AttnProcessor()
        )

    def _apply_cpu_offload(self, attr_val):
        """
        Apply sequential CPU offload for maximum VRAM savings.

        Args:
            attr_val: Whether to enable sequential CPU offload.

        Moves model components to CPU when not in use. Slow but minimal VRAM.
        Disabled for SDXL + Compel due to compatibility issues.
        """
        enabled = AIRUNNER_MEM_USE_ENABLE_SEQUENTIAL_CPU_OFFLOAD
        if enabled is None:
            enabled = attr_val

        # Disable sequential CPU offload only for SDXL models when compel is enabled
        # due to compatibility issues with compel prompt processing and meta tensor handling
        if enabled and "SDXL" in self.version and self.use_compel:
            self.logger.warning(
                "Disabling sequential CPU offload for SDXL model with "
                "compel due to compatibility issues"
            )
            enabled = False

        if enabled and not self.memory_settings.enable_model_cpu_offload:
            self._pipe.to("cpu")
            try:
                self.logger.debug("Enabling sequential cpu offload")
                self._pipe.enable_sequential_cpu_offload(self._device_index)
            except NotImplementedError as e:
                self.logger.warning(
                    f"Error applying sequential cpu offload: {e}"
                )
                self._pipe.to(self._device)
        else:
            self.logger.debug("Sequential cpu offload disabled")

    def _apply_model_offload(self, attr_val):
        """
        Apply model CPU offload for VRAM savings.

        Args:
            attr_val: Whether to enable model CPU offload.

        Less aggressive than sequential offload, keeps active components on GPU.
        May cause stability issues with SDXL + Compel.
        """
        enabled = AIRUNNER_MEM_ENABLE_MODEL_CPU_OFFLOAD
        if enabled is None:
            enabled = attr_val

        # Add warning for SDXL models with model CPU offload when using compel
        if enabled and "SDXL" in self.version and self.use_compel:
            self.logger.warning(
                "Model CPU offload with SDXL + compel may cause "
                "stability issues"
            )

        if (
            enabled
            and not self.memory_settings.use_enable_sequential_cpu_offload
        ):
            self.logger.debug("Enabling model cpu offload")
            # self._move_stable_diffusion_to_cpu()
            self._pipe.enable_model_cpu_offload(self._device_index)
        else:
            self.logger.debug("Model cpu offload disabled")

    def _apply_tome(self, attr_val):
        """
        Apply ToMe SD (Token Merging) for faster inference.

        Args:
            attr_val: Whether to enable ToMe SD.

        ToMe merges similar tokens to reduce computation. Minimal quality loss
        with significant speedup.
        """
        enabled = AIRUNNER_MEM_USE_TOME_SD
        if enabled is None:
            enabled = attr_val
        if enabled:
            ratio = AIRUNNER_MEM_TOME_SD_RATIO
            if ratio is None:
                ratio = self.memory_settings.tome_sd_ratio / 1000
            else:
                ratio = float(ratio)
            self.logger.debug(
                f"Applying ToMe SD weight merging with ratio {ratio}"
            )
            self._remove_tome_sd()
            try:
                tomesd.apply_patch(self._pipe, ratio=ratio)
            except Exception as e:
                self.logger.error(
                    f"Error applying ToMe SD weight merging: {e}"
                )
        else:
            self._remove_tome_sd()

    def _apply_xformers(self):
        """
        Apply xformers memory-efficient attention (Flash Attention 2).

        This provides significant speedup on modern GPUs (RTX 30xx/40xx).
        Can be disabled via AIRUNNER_DISABLE_FLASH_ATTENTION environment variable.
        """
        if AIRUNNER_DISABLE_FLASH_ATTENTION:
            self.logger.debug(
                "xformers disabled via AIRUNNER_DISABLE_FLASH_ATTENTION"
            )
            return

        if not is_ampere_or_newer(self._device_index):
            self.logger.debug(
                "xformers requires Ampere or newer GPU (RTX 30xx/40xx+)"
            )
            return

        try:
            if hasattr(
                self._pipe, "enable_xformers_memory_efficient_attention"
            ):
                self._pipe.enable_xformers_memory_efficient_attention()
                self.logger.info(
                    "✓ Enabled xformers memory-efficient attention (Flash Attention 2)"
                )
            else:
                self.logger.debug("Pipeline does not support xformers")
        except Exception as e:
            self.logger.warning(f"Could not enable xformers: {e}")
            self.logger.debug(
                "Install xformers for Flash Attention 2: pip install xformers"
            )

    def _apply_torch_compile(self):
        """
        Apply torch.compile() to UNet for 2-3x inference speedup.

        NOTE: torch.compile() is lazy - it wraps the model but doesn't compile
        until the first forward pass. This means:
        - Wrapping is instant (happens here)
        - Compilation is slow (happens during first generation, 2-3 minutes)
        - Cache persists per input shape (different resolutions = recompile)

        Only applies once per pipeline load to avoid recompilation overhead.

        Note: DeepCache has been permanently disabled as it's incompatible
        with torch.compile() and provides inferior speedup (15% vs 2-3x).
        """
        settings = get_qsettings()
        settings.beginGroup("generator_settings")
        enable_torch_compile = settings.value(
            "enable_torch_compile", False, type=bool
        )
        settings.endGroup()
        print("APPLY TORCH COMPILE")
        print("-" * 100)
        print(enable_torch_compile)
        if not enable_torch_compile:
            return

        if self._memory_settings_flags.get("torch_compile_applied"):
            return  # Already compiled

        if not hasattr(self._pipe, "unet") or self._pipe.unet is None:
            return

        try:
            self.logger.info(
                "Wrapping UNet with torch.compile() - compilation will happen on first generation"
            )
            # Note: torch.compile caches are stored in PyTorch's internal cache
            # directory (~/.triton or TORCH_COMPILE_DIR). They persist across runs
            # and are reused when the same model graph AND input shapes are seen.
            self._pipe.unet = torch.compile(
                self._pipe.unet,
                mode="reduce-overhead",  # Best for inference
                fullgraph=False,  # Allow fallback for unsupported ops
            )
            self._memory_settings_flags["torch_compile_applied"] = True
            self.logger.info(
                "✓ UNet wrapped for compilation (first generation will take 2-3 min)"
            )
            self.logger.debug(
                "Compiled cache stored in ~/.triton per input shape (resolution/batch)"
            )
        except Exception as e:
            self.logger.warning(f"Could not compile UNet: {e}")
            self.logger.debug("torch.compile requires PyTorch 2.0+")

    def _remove_tome_sd(self):
        """
        Remove ToMe SD patch from pipeline.

        Restores normal token processing.
        """
        self.logger.debug("Removing ToMe SD weight merging")
        try:
            tomesd.remove_patch(self._pipe)
        except Exception as e:
            self.logger.error(f"Error removing ToMe SD weight merging: {e}")

    def _clear_memory_efficient_settings(self):
        """
        Clear all memory efficiency flags.

        Forces reapplication of memory settings on next call.
        """
        self.logger.debug("Clearing memory efficient settings")
        for key in self._memory_settings_flags:
            if key.endswith("_applied"):
                self._memory_settings_flags[key] = None
