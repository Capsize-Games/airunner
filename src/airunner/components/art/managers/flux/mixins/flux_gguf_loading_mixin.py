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
        self, model_path: Path, config_path: Path
    ) -> FluxTransformer2DModel:
        """Load GGUF quantized transformer."""
        self.logger.info(f"Loading GGUF FLUX transformer from: {model_path}")
        transformer = FluxTransformer2DModel.from_single_file(
            str(model_path),
            config=str(config_path),
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
        """Load GGUF FLUX model with all components."""
        self.logger.info(f"Loading GGUF FLUX model: {model_path}")
        self.emit_signal(
            SignalCode.UPDATE_DOWNLOAD_LOG,
            {"message": "Loading GGUF FLUX model (already quantized)..."},
        )

        companion_dir = Path(model_path).parent
        config_path = companion_dir / "transformer" / "config.json"

        # Load transformer
        transformer = self._load_gguf_transformer(model_path, config_path)

        # Load other components
        components = self._load_pipeline_components(companion_dir)

        # Create pipeline
        self._pipe = pipeline_class(transformer=transformer, **components)

        # CRITICAL: Ensure VAE is in float32 for proper decoding
        self._force_vae_fp32()

        self.logger.info("✓ Loaded GGUF FLUX pipeline")
