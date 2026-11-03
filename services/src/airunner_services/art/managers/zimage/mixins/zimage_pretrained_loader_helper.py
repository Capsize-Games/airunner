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
from airunner_services.art.managers.zimage.zimage_resource_budget import (
    ZImageMemoryPlan,
    build_zimage_memory_plan,
)
from airunner_services.model_management import ModelResourceManager


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
        if use_quant and quant_bits not in (4, 8):
            raise RuntimeError(
                f"Pretrained Z-Image does not support {quant_bits}-bit "
                "quantization"
            )
        selected_bits = quant_bits if use_quant else None
        plan = getattr(self._owner, "_zimage_memory_plan", None)
        if (
            not isinstance(plan, ZImageMemoryPlan)
            or plan.quantization_bits != selected_bits
        ):
            plan = self.build_memory_plan(
                model_dir,
                use_quantization=use_quant,
                quantization_bits=selected_bits,
            )
            self._owner._zimage_memory_plan = plan
        self._check_live_capacity(
            "transformer",
            plan.gpu_weight_budget_gib + plan.gpu_activation_reserve_gib,
            plan.cpu_weight_budget_gib + plan.cpu_workspace_gib,
        )
        transformer_cfg, text_encoder_cfg = self._build_quantization_configs(
            use_quant,
            quant_bits,
        )
        transformer, text_encoder, tokenizer, vae = self._load_components(
            model_dir,
            transformer_cfg,
            text_encoder_cfg,
            model_dtype,
            plan,
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
        plan: ZImageMemoryPlan,
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
            plan.max_memory_transformer,
        )
        if transformer is None:
            raise RuntimeError("Failed to load transformer")
        self._check_live_capacity(
            "text encoder",
            plan.text_encoder_gpu_gib + plan.vae_gpu_gib
            + plan.gpu_activation_reserve_gib,
            plan.text_encoder_cpu_gib + plan.vae_cpu_gib
            + plan.cpu_workspace_gib,
        )
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
            plan.max_memory_text_encoder,
        )
        if text_encoder is None:
            raise RuntimeError("Failed to load text encoder")
        self._check_live_capacity(
            "VAE",
            plan.vae_gpu_gib + plan.gpu_activation_reserve_gib,
            plan.vae.estimated_resident_gib + plan.cpu_workspace_gib,
        )
        vae_path = model_dir / "vae"
        self._owner.logger.info("Loading VAE from %s", vae_path)
        vae = self.load_vae_from_pretrained(vae_path, model_dtype)
        if vae is None:
            raise RuntimeError("Failed to load VAE")
        self._check_live_capacity(
            "VAE placement",
            (
                plan.gpu_weight_budget_gib
                if not use_quant
                else plan.vae_gpu_gib
            )
            + plan.gpu_activation_reserve_gib,
            plan.cpu_workspace_gib,
        )
        return transformer, text_encoder, tokenizer, vae

    def build_memory_plan(
        self,
        model_dir: Path,
        *,
        use_quantization: bool,
        quantization_bits: Optional[int],
    ) -> ZImageMemoryPlan:
        """Build a source-derived estimate from the current host profile."""
        resource_manager = ModelResourceManager()
        profile = resource_manager.hardware_profiler.get_profile()
        if use_quantization and not profile.cuda_available:
            raise RuntimeError(
                "Quantized Z-Image preflight requires CUDA; the live PyTorch "
                "runtime did not report an available CUDA device"
            )
        return build_zimage_memory_plan(
            model_dir,
            available_vram_gib=profile.available_vram_gb,
            available_ram_gib=profile.available_ram_gb,
            reserved_vram_gib=resource_manager.memory_allocator._reserved_vram_gb,
            reserved_ram_gib=resource_manager.memory_allocator._reserved_ram_gb,
            quantization_bits=(quantization_bits if use_quantization else None),
            target_dtype_bytes=(
                4 if self._owner.data_type == torch.float32 else 2
            ),
        )

    def _check_live_capacity(
        self,
        stage: str,
        required_vram_gib: float,
        required_ram_gib: float,
    ) -> None:
        """Recheck live headroom before each component allocation."""
        resource_manager = ModelResourceManager()
        model_id = str(getattr(self._owner, "model_path", ""))
        allowed, reason, profile = resource_manager.check_live_load_capacity(
            model_id,
            required_vram_gb=required_vram_gib,
            required_ram_gb=required_ram_gib,
        )
        self._owner.logger.info(
            "Z-Image %s budget check: VRAM=%.2f GiB RAM=%.2f GiB",
            stage,
            profile.available_vram_gb,
            profile.available_ram_gb,
        )
        if not allowed:
            raise RuntimeError(f"Z-Image {stage} preflight failed: {reason}")

    def compute_max_memory_for_models(self, use_quant: bool) -> Optional[dict]:
        """Compute memory caps without exceeding current free resources."""
        if not torch.cuda.is_available() or not use_quant:
            return None
        profile = ModelResourceManager().hardware_profiler.get_profile()
        memory_manager = ModelResourceManager().memory_allocator
        usable_vram_gb = max(
            0.0,
            profile.available_vram_gb - memory_manager._reserved_vram_gb,
        )
        usable_ram_gb = max(
            0.0,
            profile.available_ram_gb - memory_manager._reserved_ram_gb,
        )
        if usable_vram_gb <= 0.0 or usable_ram_gb <= 0.0:
            raise RuntimeError(
                "Insufficient live VRAM or RAM for quantized model loading"
            )
        self._owner.logger.info(
            "Live model placement caps: VRAM=%.2f GiB RAM=%.2f GiB",
            usable_vram_gb,
            usable_ram_gb,
        )
        return {
            0: f"{usable_vram_gb:.2f}GiB",
            "cpu": f"{usable_ram_gb:.2f}GiB",
        }

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
                trust_remote_code=False,
                **load_kwargs,
            )
            tokenizer = AutoTokenizer.from_pretrained(
                str(tokenizer_path),
                local_files_only=True,
                trust_remote_code=False,
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
