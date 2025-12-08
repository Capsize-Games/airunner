# Copyright 2025 AI Runner. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# LoRA loader mixin for Z-Image pipelines, adapted from SanaLoraLoaderMixin.

import os
from typing import Callable, Dict, List, Optional, Union

import torch

from diffusers.loaders.lora_base import LoraBaseMixin, _fetch_state_dict
from diffusers.utils import (
    USE_PEFT_BACKEND,
    is_peft_version,
    logging,
)


logger = logging.get_logger(__name__)

TRANSFORMER_NAME = "transformer"

# Default value for low CPU memory usage - matches diffusers behavior
_LOW_CPU_MEM_USAGE_DEFAULT_LORA = False
try:
    # Try to enable if peft supports it
    if is_peft_version(">=", "0.13.0"):
        _LOW_CPU_MEM_USAGE_DEFAULT_LORA = True
except Exception:
    pass


class ZImageLoraLoaderMixin(LoraBaseMixin):
    """
    Load LoRA layers into ZImageTransformer2DModel. Specific to ZImagePipeline.
    
    This mixin provides LoRA support for Z-Image models, allowing users to load
    and apply LoRA weights to the transformer component.
    
    Note: Z-Image text encoder (Qwen2-VL) does not support LoRA via this mixin.
    Only transformer LoRA is supported.
    """

    _lora_loadable_modules = ["transformer"]
    transformer_name = TRANSFORMER_NAME

    @classmethod
    def lora_state_dict(
        cls,
        pretrained_model_name_or_path_or_dict: Union[str, Dict[str, torch.Tensor]],
        **kwargs,
    ):
        """
        Return state dict for LoRA weights.
        
        Args:
            pretrained_model_name_or_path_or_dict: Path or dict of LoRA weights.
            
        Returns:
            State dict containing LoRA weights.
        """
        cache_dir = kwargs.pop("cache_dir", None)
        force_download = kwargs.pop("force_download", False)
        proxies = kwargs.pop("proxies", None)
        local_files_only = kwargs.pop("local_files_only", None)
        token = kwargs.pop("token", None)
        revision = kwargs.pop("revision", None)
        subfolder = kwargs.pop("subfolder", None)
        weight_name = kwargs.pop("weight_name", None)
        use_safetensors = kwargs.pop("use_safetensors", None)
        return_lora_metadata = kwargs.pop("return_lora_metadata", False)

        allow_pickle = False
        if use_safetensors is None:
            use_safetensors = True
            allow_pickle = True

        user_agent = {"file_type": "attn_procs_weights", "framework": "pytorch"}

        state_dict, metadata = _fetch_state_dict(
            pretrained_model_name_or_path_or_dict=pretrained_model_name_or_path_or_dict,
            weight_name=weight_name,
            use_safetensors=use_safetensors,
            local_files_only=local_files_only,
            cache_dir=cache_dir,
            force_download=force_download,
            proxies=proxies,
            token=token,
            revision=revision,
            subfolder=subfolder,
            user_agent=user_agent,
            allow_pickle=allow_pickle,
        )

        # Filter out DoRA scale keys if present (not supported)
        is_dora_scale_present = any("dora_scale" in k for k in state_dict)
        if is_dora_scale_present:
            logger.warning(
                "DoRA checkpoints are not compatible with Z-Image at the moment. "
                "Filtering out 'dora_scale' keys from the state dict."
            )
            state_dict = {k: v for k, v in state_dict.items() if "dora_scale" not in k}

        out = (state_dict, metadata) if return_lora_metadata else state_dict
        return out

    def load_lora_weights(
        self,
        pretrained_model_name_or_path_or_dict: Union[str, Dict[str, torch.Tensor]],
        adapter_name: Optional[str] = None,
        hotswap: bool = False,
        **kwargs,
    ):
        """
        Load LoRA weights into the pipeline's transformer.
        
        Args:
            pretrained_model_name_or_path_or_dict: Path, HuggingFace repo ID, or state dict.
            adapter_name: Name for the adapter (for multi-adapter support).
            hotswap: If True, replace existing adapter with same name.
            **kwargs: Additional arguments.
            
        Raises:
            ValueError: If PEFT backend is not available or checkpoint is invalid.
        """
        if not USE_PEFT_BACKEND:
            raise ValueError("PEFT backend is required for LoRA. Install with: pip install peft")

        low_cpu_mem_usage = kwargs.pop("low_cpu_mem_usage", _LOW_CPU_MEM_USAGE_DEFAULT_LORA)
        if low_cpu_mem_usage and is_peft_version("<", "0.13.0"):
            raise ValueError(
                "`low_cpu_mem_usage=True` requires peft>=0.13.0. Update with: pip install -U peft"
            )

        # Copy dict to avoid modifying original
        if isinstance(pretrained_model_name_or_path_or_dict, dict):
            pretrained_model_name_or_path_or_dict = pretrained_model_name_or_path_or_dict.copy()

        # Load state dict and validate format
        kwargs["return_lora_metadata"] = True
        state_dict, metadata = self.lora_state_dict(pretrained_model_name_or_path_or_dict, **kwargs)

        is_correct_format = all("lora" in key for key in state_dict.keys())
        if not is_correct_format:
            raise ValueError("Invalid LoRA checkpoint format. Keys must contain 'lora'.")

        self.load_lora_into_transformer(
            state_dict,
            transformer=getattr(self, self.transformer_name) if not hasattr(self, "transformer") else self.transformer,
            adapter_name=adapter_name,
            metadata=metadata,
            _pipeline=self,
            low_cpu_mem_usage=low_cpu_mem_usage,
            hotswap=hotswap,
        )

    @classmethod
    def load_lora_into_transformer(
        cls,
        state_dict,
        transformer,
        adapter_name=None,
        _pipeline=None,
        low_cpu_mem_usage=False,
        hotswap: bool = False,
        metadata=None,
    ):
        """
        Load LoRA weights into the transformer model.
        
        Args:
            state_dict: LoRA state dict.
            transformer: The transformer model to load into.
            adapter_name: Name for the adapter.
            _pipeline: The pipeline instance.
            low_cpu_mem_usage: Use low memory mode.
            hotswap: Replace existing adapter with same name.
            metadata: LoRA metadata.
        """
        if low_cpu_mem_usage and is_peft_version("<", "0.13.0"):
            raise ValueError(
                "`low_cpu_mem_usage=True` requires peft>=0.13.0. Update with: pip install -U peft"
            )

        logger.info(f"Loading LoRA weights into {cls.transformer_name}")

        # Extend PEFT's supported modules to include FP8Linear so native FP8 layers are patchable.
        # Import here to avoid circular import with fp8_ops -> native -> lora_loader
        try:
            from peft.tuners.lora import LoraLayer
            from airunner.components.art.managers.zimage.native.fp8_ops import FP8Linear

            if hasattr(LoraLayer, "SUPPORTED_LORA_MODULES"):
                if FP8Linear not in LoraLayer.SUPPORTED_LORA_MODULES:
                    LoraLayer.SUPPORTED_LORA_MODULES = (
                        *LoraLayer.SUPPORTED_LORA_MODULES,
                        FP8Linear,
                    )
            else:
                # Older PEFT versions use SUPPORTED_MODULES
                if hasattr(LoraLayer, "SUPPORTED_MODULES") and FP8Linear not in LoraLayer.SUPPORTED_MODULES:
                    LoraLayer.SUPPORTED_MODULES = (
                        *LoraLayer.SUPPORTED_MODULES,
                        FP8Linear,
                    )
        except Exception:
            # Best effort; fallback to default behavior
            pass
        
        # Z-Image LoRAs use "diffusion_model." prefix in their keys
        # We need to tell load_lora_adapter to strip this prefix
        # If the state dict has keys starting with "diffusion_model.", use that as prefix
        # Otherwise, use None to avoid filtering
        sample_key = next(iter(state_dict.keys()), "")
        if sample_key.startswith("diffusion_model."):
            prefix = "diffusion_model"
        else:
            prefix = None
        
        transformer.load_lora_adapter(
            state_dict,
            prefix=prefix,
            hotswap=hotswap,
            network_alphas=None,
            adapter_name=adapter_name,
            low_cpu_mem_usage=low_cpu_mem_usage,
        )

    @classmethod
    def save_lora_weights(
        cls,
        save_directory: Union[str, os.PathLike],
        transformer_lora_layers: Dict[str, Union[torch.nn.Module, torch.Tensor]] = None,
        is_main_process: bool = True,
        weight_name: str = None,
        save_function: Callable = None,
        safe_serialization: bool = True,
        transformer_lora_adapter_metadata: Optional[dict] = None,
    ):
        """
        Save LoRA weights to a directory.
        
        Args:
            save_directory: Directory to save weights to.
            transformer_lora_layers: LoRA layers to save.
            is_main_process: Whether this is the main process (for distributed).
            weight_name: Custom weight filename.
            save_function: Custom save function.
            safe_serialization: Use safetensors format.
            transformer_lora_adapter_metadata: Metadata to save with weights.
        """
        lora_layers = {}
        lora_metadata = {}

        if transformer_lora_layers:
            lora_layers[cls.transformer_name] = transformer_lora_layers
            lora_metadata[cls.transformer_name] = transformer_lora_adapter_metadata

        if not lora_layers:
            raise ValueError("You must provide `transformer_lora_layers` to save.")

        cls._save_lora_weights(
            save_directory=save_directory,
            lora_layers=lora_layers,
            lora_metadata=lora_metadata,
            is_main_process=is_main_process,
            weight_name=weight_name,
            save_function=save_function,
            safe_serialization=safe_serialization,
        )

    def fuse_lora(
        self,
        components: List[str] = ["transformer"],
        lora_scale: float = 1.0,
        safe_fusing: bool = False,
        adapter_names: Optional[List[str]] = None,
        **kwargs,
    ):
        """
        Fuse LoRA weights into the base model weights.
        
        After fusing, LoRA is applied permanently and cannot be removed without
        reloading the original model.
        
        Args:
            components: Components to fuse (only "transformer" supported).
            lora_scale: Scale factor for LoRA weights.
            safe_fusing: Check for NaN/Inf after fusing.
            adapter_names: Specific adapters to fuse.
        """
        super().fuse_lora(
            components=components,
            lora_scale=lora_scale,
            safe_fusing=safe_fusing,
            adapter_names=adapter_names,
            **kwargs,
        )

    def unfuse_lora(self, components: List[str] = ["transformer"], **kwargs):
        """
        Unfuse LoRA weights from the base model weights.
        
        Only works if LoRA was fused with `safe_fusing=True`.
        
        Args:
            components: Components to unfuse (only "transformer" supported).
        """
        super().unfuse_lora(components=components, **kwargs)
