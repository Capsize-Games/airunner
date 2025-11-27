"""FLUX GGUF model loading mixin."""

from pathlib import Path
from typing import Any, Dict, Tuple
import torch
from diffusers import (
    FluxTransformer2DModel,
    GGUFQuantizationConfig,
    AutoencoderKL,
    FlowMatchEulerDiscreteScheduler,
)
from transformers import (
    CLIPTokenizer,
    T5TokenizerFast,
    CLIPTextModel,
    T5EncoderModel,
)

from airunner.enums import SignalCode


class FluxGGUFLoadingMixin:
    """Handles GGUF-specific model loading for FLUX."""

    def _load_gguf_transformer(
        self, model_path: Path, base_model_path: str
    ) -> FluxTransformer2DModel:
        """Load GGUF quantized transformer.
        
        Args:
            model_path: Path to the GGUF file
            base_model_path: Path to the base FLUX model for config
        """
        self.logger.info(f"Loading GGUF FLUX transformer from: {model_path}")
        self.logger.info(f"Using config from: {base_model_path}")
        
        transformer = FluxTransformer2DModel.from_single_file(
            str(model_path),
            config=base_model_path,
            subfolder="transformer",
            quantization_config=GGUFQuantizationConfig(
                compute_dtype=torch.bfloat16
            ),
            torch_dtype=torch.bfloat16,
        )

        self.logger.info(
            "✓ Loaded GGUF transformer (will stream to GPU during inference)"
        )
        return transformer

    def _load_pipeline_components(self, companion_dir: Path) -> Dict[str, Any]:
        """Load tokenizers, text encoders, VAE, and scheduler."""
        tokenizer, tokenizer_2 = self._load_tokenizers(companion_dir)
        text_encoder, text_encoder_2 = self._load_text_encoders(companion_dir)
        vae = self._load_flux_vae(companion_dir)
        scheduler = self._load_scheduler_component(companion_dir)

        return {
            "tokenizer": tokenizer,
            "tokenizer_2": tokenizer_2,
            "text_encoder": text_encoder,
            "text_encoder_2": text_encoder_2,
            "vae": vae,
            "scheduler": scheduler,
        }

    def _load_tokenizers(self, companion_dir: Path) -> Tuple[Any, Any]:
        """Load CLIP and T5 tokenizers."""
        tokenizer = CLIPTokenizer.from_pretrained(
            str(companion_dir / "tokenizer"), local_files_only=True
        )
        tokenizer_2 = T5TokenizerFast.from_pretrained(
            str(companion_dir / "tokenizer_2"), local_files_only=True
        )
        return tokenizer, tokenizer_2

    def _load_text_encoders(self, companion_dir: Path) -> Tuple[Any, Any]:
        """Load CLIP and T5 text encoders in bfloat16."""
        text_encoder = CLIPTextModel.from_pretrained(
            str(companion_dir / "text_encoder"),
            torch_dtype=torch.bfloat16,
            local_files_only=True,
        )
        text_encoder_2 = T5EncoderModel.from_pretrained(
            str(companion_dir / "text_encoder_2"),
            torch_dtype=torch.bfloat16,
            local_files_only=True,
        )
        return text_encoder, text_encoder_2

    def _load_flux_vae(self, companion_dir: Path) -> AutoencoderKL:
        """Load FLUX VAE in float32 (equivalent to --no-half)."""
        return AutoencoderKL.from_pretrained(
            str(companion_dir / "vae"),
            torch_dtype=torch.float32,
            local_files_only=True,
        )

    def _load_scheduler_component(
        self, companion_dir: Path
    ) -> FlowMatchEulerDiscreteScheduler:
        """Load FlowMatchEulerDiscreteScheduler from companion files."""
        return FlowMatchEulerDiscreteScheduler.from_pretrained(
            str(companion_dir / "scheduler"),
            subfolder=None,
            local_files_only=True,
        )

    def _load_gguf_model(self, model_path: Path, pipeline_class: Any) -> None:
        """Load GGUF FLUX model with all components.
        
        Uses the diffusers pattern:
        1. Load transformer from GGUF with base model config
        2. Load full pipeline from base model
        3. Swap in the GGUF transformer
        """
        self.logger.info(f"Loading GGUF FLUX model: {model_path}")
        self.emit_signal(
            SignalCode.UPDATE_DOWNLOAD_LOG,
            {"message": "Loading GGUF FLUX model (already quantized)..."},
        )

        model_path = Path(model_path)
        
        # Get the base FLUX model path for config and companion files
        base_model = self._base_flux_model_path()
        self.logger.info(f"Using base FLUX model: {base_model}")

        # Load transformer from GGUF using base model for config
        transformer = self._load_gguf_transformer(model_path, base_model)

        # Load the full pipeline from base model
        self.logger.info("Loading pipeline from base model...")
        self._pipe = pipeline_class.from_pretrained(
            base_model,
            transformer=transformer,
            torch_dtype=torch.bfloat16,
            local_files_only=True,
        )

        # Enable CPU offload for memory efficiency
        self._pipe.enable_model_cpu_offload()

        # CRITICAL: Ensure VAE is in float32 for proper decoding
        self._force_vae_fp32()

        self.logger.info("✓ Loaded GGUF FLUX pipeline")
