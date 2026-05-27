"""Pretrained Z-Image loading helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

import torch
from diffusers import AutoencoderKL
from diffusers import BitsAndBytesConfig as DiffusersBnBConfig
from transformers import AutoModelForCausalLM, AutoTokenizer
from transformers import BitsAndBytesConfig as TransformersBnBConfig

from airunner_services.art.pipelines.z_image import ZImageTransformer2DModel


class ZImagePretrainedLoaderHelper:
    """Load Z-Image components from a pretrained directory."""

    def __init__(self, owner) -> None:
        """Store the owning loading mixin instance."""
        self._owner = owner

    def load_from_pretrained(
        self,
        model_path: str,
        pipeline_class: Any,
        data: dict,
    ) -> None:
        """Load a complete pretrained Z-Image pipeline."""
        del data
        self._owner.logger.info("Loading Z-Image from pretrained: %s", model_path)
        model_dir = Path(model_path)
        use_quant, quant_bits, model_dtype = self._resolve_precision_settings()
        max_memory = self.compute_max_memory_for_models(use_quant)
        transformer_cfg, text_encoder_cfg = self._build_quantization_configs(
            use_quant,
            quant_bits,
        )
        transformer, text_encoder, tokenizer, vae = self._load_components(
            model_dir,
            transformer_cfg,
            text_encoder_cfg,
            model_dtype,
            max_memory,
            use_quant,
            quant_bits,
        )
        scheduler = self._owner._get_runtime_loader_helper().load_zimage_scheduler(
            model_dir / "scheduler"
        )
        self._owner.logger.info("Assembling ZImagePipeline from components...")
        try:
            self._owner._pipe = self.assemble_pipeline(
                pipeline_class,
                transformer,
                vae,
                text_encoder,
                tokenizer,
                scheduler,
            )
            precision = self._precision_label(use_quant, quant_bits, model_dtype)
            self._owner.logger.info(
                "Pipeline assembled successfully (%s)",
                precision,
            )
        except Exception as exc:
            self._owner.logger.error("Failed to assemble pipeline: %s", exc)
            raise

    def _resolve_precision_settings(
        self,
    ) -> tuple[bool, Optional[int], torch.dtype]:
        """Resolve quantization and dtype settings for this load."""
        use_quant = getattr(self._owner, "use_quantization", False)
        quant_bits = getattr(self._owner, "quantization_bits", None)
        model_dtype = self._owner.data_type
        if getattr(self._owner, "_force_quantization_for_fp8_fallback", False):
            self._owner.logger.info(
                "FP8 fallback mode - forcing 4-bit quantization for "
                "transformer and text encoder"
            )
            use_quant = True
            quant_bits = 4
            self._owner._force_quantization_for_fp8_fallback = False
        self._owner.logger.info(
            "Precision settings - use_quantization: %s, bits: %s, "
            "dtype: %s",
            use_quant,
            quant_bits,
            model_dtype,
        )
        return use_quant, quant_bits, model_dtype

    def _build_quantization_configs(
        self,
        use_quant: bool,
        quant_bits: Optional[int],
    ) -> tuple[Optional[DiffusersBnBConfig], Optional[TransformersBnBConfig]]:
        """Create BitsAndBytes configs for transformer and text encoder."""
        if use_quant and quant_bits == 4:
            self._owner.logger.info("Using 4-bit NF4 quantization")
            return (
                DiffusersBnBConfig(
                    load_in_4bit=True,
                    bnb_4bit_compute_dtype=torch.bfloat16,
                    bnb_4bit_use_double_quant=True,
                    bnb_4bit_quant_type="nf4",
                ),
                TransformersBnBConfig(
                    load_in_4bit=True,
                    bnb_4bit_compute_dtype=torch.bfloat16,
                    bnb_4bit_use_double_quant=True,
                    bnb_4bit_quant_type="nf4",
                ),
            )
        if use_quant and quant_bits == 8:
            self._owner.logger.info("Using 8-bit quantization")
            return (
                DiffusersBnBConfig(load_in_8bit=True),
                TransformersBnBConfig(load_in_8bit=True),
            )
        self._owner.logger.info("No quantization requested for pretrained load")
        return None, None

    def _load_components(
        self,
        model_dir: Path,
        transformer_cfg: Optional[DiffusersBnBConfig],
        text_encoder_cfg: Optional[TransformersBnBConfig],
        model_dtype: torch.dtype,
        max_memory: Optional[dict],
        use_quant: bool,
        quant_bits: Optional[int],
    ) -> tuple[Any, Any, Any, Any]:
        """Load pretrained transformer, text encoder, tokenizer, and VAE."""
        quant_info = self._precision_label(use_quant, quant_bits, model_dtype)
        transformer_path = model_dir / "transformer"
        self._owner.logger.info(
            "Loading transformer from %s (%s)",
            transformer_path,
            quant_info,
        )
        transformer = self.load_transformer_from_pretrained(
            transformer_path,
            transformer_cfg,
            model_dtype,
            max_memory,
        )
        if transformer is None:
            raise RuntimeError("Failed to load transformer")
        text_encoder_path = model_dir / "text_encoder"
        tokenizer_path = model_dir / "tokenizer"
        self._owner.logger.info(
            "Loading text encoder from %s (%s)",
            text_encoder_path,
            quant_info,
        )
        text_encoder, tokenizer = self.load_text_encoder_from_pretrained(
            text_encoder_path,
            tokenizer_path,
            text_encoder_cfg,
            model_dtype,
            max_memory,
        )
        if text_encoder is None:
            raise RuntimeError("Failed to load text encoder")
        vae_path = model_dir / "vae"
        self._owner.logger.info("Loading VAE from %s", vae_path)
        vae = self.load_vae_from_pretrained(vae_path, model_dtype)
        if vae is None:
            raise RuntimeError("Failed to load VAE")
        return transformer, text_encoder, tokenizer, vae

    def compute_max_memory_for_models(self, use_quant: bool) -> Optional[dict]:
        """Compute one max-memory mapping for quantized component loads."""
        if not torch.cuda.is_available() or not use_quant:
            return None
        total_vram = torch.cuda.get_device_properties(0).total_memory / (1024**3)
        reserved_gb = 3.0
        usable_vram_gb = max(total_vram - reserved_gb, 4.0)
        self._owner.logger.info(
            "VRAM budget: %.1fGB for models (reserving %.1fGB for "
            "VAE/activations)",
            usable_vram_gb,
            reserved_gb,
        )
        return {0: f"{usable_vram_gb:.0f}GiB", "cpu": "32GiB"}

    def load_transformer_from_pretrained(
        self,
        transformer_path: Path,
        transformer_bnb_config: Optional[DiffusersBnBConfig],
        model_dtype: torch.dtype,
        max_memory_for_models: Optional[dict],
    ) -> Any:
        """Load a pretrained transformer component."""
        try:
            load_kwargs = {"torch_dtype": model_dtype, "local_files_only": True}
            if transformer_bnb_config is not None:
                load_kwargs["quantization_config"] = transformer_bnb_config
                load_kwargs["device_map"] = "auto"
                if max_memory_for_models is not None:
                    load_kwargs["max_memory"] = max_memory_for_models
            return ZImageTransformer2DModel.from_pretrained(
                str(transformer_path),
                **load_kwargs,
            )
        except Exception as exc:
            self._owner.logger.error("Failed to load transformer: %s", exc)
            return None

    def load_text_encoder_from_pretrained(
        self,
        text_encoder_path: Any,
        tokenizer_path: Any,
        text_encoder_bnb_config: Optional[TransformersBnBConfig],
        model_dtype: torch.dtype,
        max_memory_for_models: Optional[dict],
    ) -> tuple[Any, Any]:
        """Load the text encoder and tokenizer from pretrained assets."""
        self._owner.logger.info("Loading text encoder from %s", text_encoder_path)
        try:
            load_kwargs = {"local_files_only": True}
            if text_encoder_bnb_config is not None:
                load_kwargs["quantization_config"] = text_encoder_bnb_config
                load_kwargs["device_map"] = "auto"
                if max_memory_for_models is not None:
                    load_kwargs["max_memory"] = max_memory_for_models
            else:
                load_kwargs["torch_dtype"] = model_dtype
            text_encoder = AutoModelForCausalLM.from_pretrained(
                str(text_encoder_path),
                **load_kwargs,
            )
            tokenizer = AutoTokenizer.from_pretrained(
                str(tokenizer_path),
                local_files_only=True,
            )
            return text_encoder, tokenizer
        except Exception as exc:
            self._owner.logger.error("Failed to load text encoder: %s", exc)
            return None, None

    def load_vae_from_pretrained(
        self,
        vae_path: Any,
        model_dtype: torch.dtype,
    ) -> Any:
        """Load the VAE from pretrained assets."""
        self._owner.logger.info("Loading VAE from %s", vae_path)
        try:
            return AutoencoderKL.from_pretrained(
                str(vae_path),
                torch_dtype=model_dtype,
                local_files_only=True,
            )
        except Exception as exc:
            self._owner.logger.error("Failed to load VAE: %s", exc)
            return None

    @staticmethod
    def assemble_pipeline(
        pipeline_class: Any,
        transformer: Any,
        vae: Any,
        text_encoder: Any,
        tokenizer: Any,
        scheduler: Any,
    ) -> Any:
        """Create one pipeline instance from prepared components."""
        return pipeline_class(
            transformer=transformer,
            vae=vae,
            text_encoder=text_encoder,
            tokenizer=tokenizer,
            scheduler=scheduler,
        )

    @staticmethod
    def _precision_label(
        use_quant: bool,
        quant_bits: Optional[int],
        model_dtype: torch.dtype,
    ) -> str:
        """Return one concise label describing the active precision mode."""
        if use_quant and quant_bits is not None:
            return f"{quant_bits}-bit quantized"
        return f"dtype: {model_dtype}"