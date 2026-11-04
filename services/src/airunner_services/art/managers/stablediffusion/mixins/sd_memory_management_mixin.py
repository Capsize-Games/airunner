"""
Mixin providing memory optimization for Stable Diffusion models.

This mixin handles all memory efficiency settings including VAE slicing,
attention slicing, CPU offload, ToMe SD, and other VRAM optimizations.
"""

import re
from dataclasses import asdict, is_dataclass

import torch
import tomesd
from diffusers.models.attention_processor import (
    AttnProcessor,
    AttnProcessor2_0,
)

from airunner_common.settings import (
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
from airunner_services.art.runtime_memory import is_ampere_or_newer


class SDMemoryManagementMixin:
    """Mixin providing memory optimization for Stable Diffusion models."""

    def _make_memory_efficient(self):
        """
        Apply all memory efficiency settings to pipeline.

        Applies settings like VAE slicing, attention slicing, CPU offload,
        ToMe SD, xformers, and torch.compile based on current memory settings.
        """
        self._current_memory_settings = self._settings_to_dict(
            self.memory_settings
        )
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

        # torch.compile is an explicit opt-in and requires the reviewed
        # external Triton toolchain. Keep the eager UNet active when the
        # environment is unsupported or incomplete.
        compile_enabled = bool(
            getattr(self.memory_settings, "use_torch_compile", False)
        )
        if (
            self._memory_settings_flags.get("torch_compile_applied")
            != compile_enabled
        ):
            if compile_enabled:
                applied = self._apply_torch_compile(True)
                self._memory_settings_flags["torch_compile_applied"] = (
                    True if applied else None
                )
            else:
                self._apply_torch_compile(False)
                self._memory_settings_flags["torch_compile_applied"] = False

    def _settings_to_dict(self, settings: object) -> dict:
        """Convert settings object to dict, supporting both ORM
        models and bridge dataclasses.

        Args:
            settings: MemorySettings ORM instance or MemorySettingsData
                      dataclass.

        Returns:
            Dictionary of setting key-value pairs.
        """
        if is_dataclass(settings):
            return asdict(settings)
        return settings.to_dict()

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

    def _apply_torch_compile(self, enabled: bool) -> bool:
        """Configure lazy UNet compilation only after the opt-in preflight.

        ``torch.compile`` creates a lazy wrapper; model compilation itself
        occurs on the first forward pass and is intentionally not triggered
        while loading a model.
        """
        if not enabled:
            owner_pipe = getattr(self, "_torch_compile_owner_pipe", None)
            original = getattr(self, "_torch_compile_original_unet", None)
            compiled = getattr(self, "_torch_compile_compiled_unet", None)
            if (
                owner_pipe is not None
                and owner_pipe is self._pipe
                and original is not None
                and compiled is not None
                and getattr(owner_pipe, "unet", None) is compiled
            ):
                owner_pipe.unet = original
            self._torch_compile_original_unet = None
            self._torch_compile_owner_pipe = None
            self._torch_compile_compiled_unet = None
            self.torch_compile_applied = False
            self._set_torch_compile_status("disabled")
            return True

        owner_pipe = getattr(self, "_torch_compile_owner_pipe", None)
        compiled_unet = getattr(self, "_torch_compile_compiled_unet", None)
        if owner_pipe is not None and (
            owner_pipe is not self._pipe
            or getattr(owner_pipe, "unet", None) is not compiled_unet
        ):
            # Release stale pipeline/module references before preflight can
            # return early on an unavailable toolchain.
            self._torch_compile_original_unet = None
            self._torch_compile_owner_pipe = None
            self._torch_compile_compiled_unet = None
            self.torch_compile_applied = False

        if not torch.cuda.is_available():
            self.torch_compile_applied = False
            self._set_torch_compile_status(
                "unavailable: CUDA is not available"
            )
            return False

        from airunner_services.art.triton_runtime import ensure_available

        available, reason = ensure_available()
        if not available:
            self.torch_compile_applied = False
            self._set_torch_compile_status(f"unavailable: {reason}")
            self.logger.warning(
                "torch.compile remains disabled; "
                "install the reviewed Triton candidate and configure its NVIDIA "
                "toolchain paths. "
                f"{reason}"
            )
            return False

        compile_pipe = self._pipe
        current_unet = compile_pipe.unet
        owner_pipe = getattr(self, "_torch_compile_owner_pipe", None)
        original = getattr(self, "_torch_compile_original_unet", None)
        compiled_unet = getattr(self, "_torch_compile_compiled_unet", None)
        if owner_pipe is not compile_pipe or current_unet is not compiled_unet:
            # A new pipeline (or a replacement UNet on the same pipeline) owns
            # its own eager module. Never restore a previous pipeline's UNet
            # over the component currently installed here.
            original = current_unet
            self._torch_compile_original_unet = original
            self._torch_compile_owner_pipe = compile_pipe
            self._torch_compile_compiled_unet = None
            compiled_unet = None

        if current_unet is original:
            try:
                compiled_unet = torch.compile(current_unet)
                compiled_forward = compiled_unet.forward

                def _forward_with_eager_fallback(*args, **kwargs):
                    try:
                        return compiled_forward(*args, **kwargs)
                    except Exception as exc:
                        if not self._is_compile_backend_failure(exc):
                            raise
                        if (
                            self._pipe is compile_pipe
                            and compile_pipe.unet is compiled_unet
                        ):
                            compile_pipe.unet = original
                        if (
                            self._pipe is compile_pipe
                            and self._torch_compile_owner_pipe is compile_pipe
                            and compile_pipe.unet is original
                        ):
                            self._torch_compile_original_unet = None
                            self._torch_compile_owner_pipe = None
                            self._torch_compile_compiled_unet = None
                            self.torch_compile_applied = False
                            self._memory_settings_flags[
                                "torch_compile_applied"
                            ] = None
                            self._set_torch_compile_status(
                                "compile failed on forward; eager UNet fallback is active"
                            )
                            self.logger.warning(
                                "torch.compile failed during UNet execution; "
                                "using the eager UNet for this and later calls: "
                                f"{type(exc).__name__}"
                            )
                        return original(*args, **kwargs)

                compiled_unet.forward = _forward_with_eager_fallback
                compile_pipe.unet = compiled_unet
                self._torch_compile_compiled_unet = compiled_unet
            except Exception as exc:
                if not self._is_compile_backend_failure(exc):
                    self._torch_compile_original_unet = None
                    self._torch_compile_owner_pipe = None
                    self._torch_compile_compiled_unet = None
                    self.torch_compile_applied = False
                    self._set_torch_compile_status(
                        "setup interrupted; eager UNet remains active"
                    )
                    raise
                if (
                    self._pipe is compile_pipe
                    and compile_pipe.unet is compiled_unet
                ):
                    compile_pipe.unet = original
                self._torch_compile_original_unet = None
                self._torch_compile_owner_pipe = None
                self._torch_compile_compiled_unet = None
                self.torch_compile_applied = False
                self._set_torch_compile_status(
                    "unavailable: compiler setup failed"
                )
                self.logger.warning(
                    "torch.compile compiler setup failed; the eager UNet remains active: "
                    f"{type(exc).__name__}"
                )
                return False
        self.torch_compile_applied = True
        self._set_torch_compile_status(
            "configured; compilation starts on the first UNet forward pass"
        )
        return True

    def _set_torch_compile_status(self, status: str) -> None:
        self.torch_compile_status = status
        flags = getattr(self, "_memory_settings_flags", None)
        if isinstance(flags, dict):
            flags["torch_compile_status"] = status

    @staticmethod
    def _is_compile_backend_failure(exc: Exception) -> bool:
        """Classify compiler failures without swallowing resource/model errors."""
        pending: list[BaseException] = [exc]
        seen: set[int] = set()
        compiler_failure = False
        while pending:
            current = pending.pop()
            identity = id(current)
            if identity in seen:
                continue
            seen.add(identity)
            module = type(current).__module__
            name = type(current).__name__
            message = str(current).lower()
            if (
                "out of memory" in message
                or "outofmemory" in message
                or re.search(r"\boom\b", message) is not None
                or name.lower() in {"outofmemoryerror", "cudaoutofmemoryerror"}
                or name.lower() == "oom"
            ):
                return False
            if (
                module.startswith("torch._dynamo")
                or module.startswith("torch._inductor")
                or module.startswith("triton.compiler")
            ) and name not in {"OutOfMemoryError", "CudaOutOfMemoryError"}:
                compiler_failure = True
            if current.__cause__ is not None:
                pending.append(current.__cause__)
            if current.__context__ is not None:
                pending.append(current.__context__)
        return compiler_failure

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
        """
        enabled = AIRUNNER_MEM_USE_ENABLE_SEQUENTIAL_CPU_OFFLOAD
        if enabled is None:
            enabled = attr_val

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
        """
        enabled = AIRUNNER_MEM_ENABLE_MODEL_CPU_OFFLOAD
        if enabled is None:
            enabled = attr_val

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
        # A pipeline swap/unload must not retain a torch.compile wrapper on
        # the reusable UNet component.
        self._apply_torch_compile(False)
        for key in self._memory_settings_flags:
            if key.endswith("_applied"):
                self._memory_settings_flags[key] = None
