"""Single-file Z-Image loading helpers."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, Optional

import torch
from transformers import BitsAndBytesConfig as TransformersBnBConfig
from airunner_services.art.managers.zimage.mixins.zimage_single_file_transformer_helper import (
    ZImageSingleFileTransformerHelper,
)


class ZImageSingleFileLoaderHelper:
    """Load Z-Image checkpoints from a single safetensors file."""

    def __init__(self, owner) -> None:
        """Store the owning loading mixin instance."""
        self._owner = owner
        self._transformer_helper = ZImageSingleFileTransformerHelper(self)

    def load_from_single_file(
        self,
        model_path: str,
        pipeline_class: Any,
        data: Dict,
        is_fp8_checkpoint: Optional[bool] = None,
    ) -> None:
        """Load one single-file Z-Image checkpoint via manual assembly."""
        self._owner.logger.info(
            "Loading Z-Image from single file: %s", model_path
        )
        use_quant = getattr(self._owner, "use_quantization", False)
        quant_bits = getattr(self._owner, "quantization_bits", None)
        model_dtype = self._owner.data_type
        is_fp8_checkpoint = self._resolve_fp8_checkpoint(
            model_path,
            is_fp8_checkpoint,
        )
        if is_fp8_checkpoint:
            self._owner.logger.info(
                "Detected FP8 pre-quantized checkpoint - transformer is "
                "already quantized"
            )
        self._owner.logger.info(
            "Precision settings - use_quantization: %s, bits: %s, dtype: %s",
            use_quant,
            quant_bits,
            model_dtype,
        )
        model_dir = self._resolve_model_dir(model_path)
        max_memory = self.compute_max_memory_for_text_encoder(
            is_fp8_checkpoint
        )
        text_encoder_cfg = self._build_text_encoder_quantization_config(
            use_quant,
            quant_bits,
            is_fp8_checkpoint,
        )
        helper = self._owner._get_pretrained_loader_helper()
        text_encoder, tokenizer = helper.load_text_encoder_from_pretrained(
            os.path.join(model_dir, "text_encoder"),
            os.path.join(model_dir, "tokenizer"),
            text_encoder_cfg,
            model_dtype,
            max_memory,
        )
        if text_encoder is None:
            raise RuntimeError("Failed to load text encoder")
        self._owner.logger.info(
            "Skipping diffusers.from_single_file for Z-Image; using manual "
            "fallback loader"
        )
        self.load_single_file_with_fallback(
            model_path,
            pipeline_class,
            text_encoder,
            tokenizer,
            data,
        )

    def _resolve_fp8_checkpoint(
        self,
        model_path: str,
        is_fp8_checkpoint: Optional[bool],
    ) -> bool:
        """Detect whether one single-file checkpoint is already FP8-quantized."""
        bundle_helper = self._owner._get_bundle_helper()
        if is_fp8_checkpoint is not None:
            return is_fp8_checkpoint
        model_filename = os.path.basename(model_path).lower()
        if any(marker in model_filename for marker in ("fp8", "e4m3", "e5m2")):
            return True
        return bundle_helper.detect_fp8_checkpoint(Path(model_path))

    def _resolve_model_dir(self, model_path: str) -> str:
        """Resolve the companion directory for one single-file checkpoint."""
        bundle_helper = self._owner._get_bundle_helper()
        checkpoint_path = Path(model_path)
        companion_dir = bundle_helper.resolve_zimage_companion_dir(
            checkpoint_path
        )
        model_dir = (
            str(companion_dir)
            if companion_dir
            else os.path.dirname(model_path)
        )
        self._owner.logger.info("Loading companion files from: %s", model_dir)
        return model_dir

    def _build_text_encoder_quantization_config(
        self,
        use_quant: bool,
        quant_bits: Optional[int],
        is_fp8_checkpoint: bool,
    ) -> Optional[TransformersBnBConfig]:
        """Create the text-encoder quantization config for single-file loads."""
        if use_quant and quant_bits == 4:
            return TransformersBnBConfig(
                load_in_4bit=True,
                bnb_4bit_compute_dtype=torch.bfloat16,
                bnb_4bit_use_double_quant=True,
                bnb_4bit_quant_type="nf4",
            )
        if use_quant and quant_bits == 8:
            return TransformersBnBConfig(load_in_8bit=True)
        if not is_fp8_checkpoint:
            return None
        self._owner.logger.info(
            "FP8 checkpoint detected - using 4-bit quantization for text "
            "encoder to save memory"
        )
        return TransformersBnBConfig(
            load_in_4bit=True,
            bnb_4bit_compute_dtype=torch.bfloat16,
            bnb_4bit_use_double_quant=True,
            bnb_4bit_quant_type="nf4",
        )

    def compute_max_memory_for_text_encoder(
        self,
        is_fp8_checkpoint: bool,
    ) -> Optional[dict]:
        """Calculate one device-map memory budget for the text encoder."""
        if not torch.cuda.is_available():
            return None
        total_vram = torch.cuda.get_device_properties(0).total_memory / (
            1024**3
        )
        reserved = 10.0 if is_fp8_checkpoint else 6.0
        budget = max(total_vram - reserved, 2.0)
        self._owner.logger.info(
            "Text encoder VRAM budget: %.1fGB (total VRAM: %.1fGB)",
            budget,
            total_vram,
        )
        return {0: f"{budget:.0f}GiB", "cpu": "24GiB"}

    def load_single_file_with_fallback(
        self,
        model_path: str,
        pipeline_class: Any,
        text_encoder: Any,
        tokenizer: Any,
        data: Dict,
    ) -> None:
        """Manually assemble one pipeline from a single checkpoint file."""
        del data
        self._owner.logger.info(
            "Attempting fallback: manual component assembly..."
        )
        helper = self._owner._get_pretrained_loader_helper()
        model_dtype = self._owner.data_type
        use_quant = getattr(self._owner, "use_quantization", False)
        quant_bits = getattr(self._owner, "quantization_bits", None)
        max_memory = helper.compute_max_memory_for_models(use_quant)
        transformer_cfg = (
            self._transformer_helper.build_transformer_quantization_config(
                use_quant,
                quant_bits,
            )
        )
        model_dir = os.path.dirname(model_path)
        transformer = self._transformer_helper.load_transformer_for_fallback(
            model_dir,
            model_path,
            transformer_cfg,
            model_dtype,
            max_memory,
            quant_bits,
            helper,
        )
        vae = helper.load_vae_from_pretrained(
            os.path.join(model_dir, "vae"),
            model_dtype,
        )
        scheduler = (
            self._owner._get_runtime_loader_helper().load_zimage_scheduler(
                Path(os.path.join(model_dir, "scheduler"))
            )
        )
        if text_encoder is None or tokenizer is None:
            text_encoder, tokenizer = (
                self._transformer_helper.load_local_text_encoder(
                    model_dir,
                    model_dtype,
                )
            )
        self._owner._pipe = pipeline_class(
            transformer=transformer,
            vae=vae,
            text_encoder=text_encoder,
            tokenizer=tokenizer,
            scheduler=scheduler,
        )
        self._owner.logger.info(
            "Fallback loading successful - pipeline assembled (dtype: %s)",
            model_dtype,
        )
