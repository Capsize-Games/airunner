"""
FLUX Model Manager for low VRAM inference.

This module provides a model manager for Black Forest Labs FLUX models,
optimized for low VRAM usage through CPU offloading, bfloat16 precision,
and optional quantization support.

FLUX variants supported:
- FLUX.1-dev: 12B parameter model, highest quality, requires more VRAM
- FLUX.1-schnell: Faster variant optimized for speed with fewer steps

VRAM Requirements:
- RTX 5080 (16GB): Supported with CPU offload
- RTX 4090 (24GB): Full model can run in VRAM
- RTX 4080 (16GB): Supported with CPU offload
- RTX 3090 (24GB): Full model can run in VRAM
- RTX 3080 (12GB): Supported with CPU offload and quantization

Optimizations applied:
- CPU offload: Moves model components between CPU/GPU as needed
- bfloat16 precision: Reduces VRAM usage by ~50%
- Sequential CPU offload: For even lower VRAM usage
- Quantization support: 8-bit and 4-bit quantization options
"""

from typing import Dict, Any, Optional
import os
from pathlib import Path
import torch
from diffusers import (
    FluxPipeline,
    FluxImg2ImgPipeline,
    FluxInpaintPipeline,
)
from transformers import BitsAndBytesConfig

from airunner.components.art.managers.stablediffusion.base_diffusers_model_manager import (
    BaseDiffusersModelManager,
)
from airunner.components.application.managers.base_model_manager import (
    ModelManagerInterface,
)
from airunner.enums import SignalCode


class FluxModelManager(BaseDiffusersModelManager, ModelManagerInterface):
    """
    Manager for FLUX text-to-image models with low VRAM optimizations.

    This manager handles loading, unloading, and generating images with
    FLUX models. It automatically applies memory optimizations based on
    available VRAM.

    Key Features:
    - Automatic CPU offload for low VRAM systems
    - bfloat16 precision by default
    - Support for quantized models
    - Sequential CPU offload for minimal VRAM usage

    Example:
        manager = FluxModelManager()
        manager.load()
        image = manager.generate(prompt="A cat holding a sign")
    """

    @property
    def img2img_pipelines(self) -> tuple:
        """Get img2img pipeline classes for FLUX."""
        return (FluxImg2ImgPipeline,)

    @property
    def txt2img_pipelines(self) -> tuple:
        """Get txt2img pipeline classes for FLUX."""
        return (FluxPipeline,)

    @property
    def controlnet_pipelines(self) -> tuple:
        """Get ControlNet pipeline classes for FLUX.

        Note: ControlNet support for FLUX is limited as of early 2025.
        This may be updated when official support is available.
        """
        return ()

    @property
    def outpaint_pipelines(self) -> tuple:
        """Get outpaint/inpaint pipeline classes for FLUX."""
        return (FluxInpaintPipeline,)

    @property
    def pipeline_map(self) -> Dict[str, Any]:
        """
        Map operation types to FLUX pipeline classes.

        Returns:
            Dict mapping operation names to pipeline classes
        """
        return {
            "txt2img": FluxPipeline,
            "img2img": FluxImg2ImgPipeline,
            "inpaint": FluxInpaintPipeline,
            "outpaint": FluxInpaintPipeline,
        }

    @property
    def _pipeline_class(self) -> Any:
        """
        Determine the appropriate pipeline class based on operation type.

        Returns:
            Pipeline class for current operation
        """
        operation_type = "txt2img"
        if self.is_img2img:
            operation_type = "img2img"
        elif self.is_inpaint:
            operation_type = "inpaint"
        elif self.is_outpaint:
            operation_type = "outpaint"

        return self.pipeline_map.get(operation_type)

    @property
    def use_from_single_file(self) -> bool:
        """
        FLUX models should use from_pretrained, not from_single_file.

        Returns:
            False to use from_pretrained
        """
        return False

    @property
    def compel_tokenizer(self) -> Any:
        """
        Get tokenizer for prompt weighting.

        Note: FLUX uses T5 tokenizer instead of CLIP.

        Returns:
            Tokenizer from pipeline
        """
        if self._pipe and hasattr(self._pipe, "tokenizer"):
            return self._pipe.tokenizer
        return None

    @property
    def compel_text_encoder(self) -> Any:
        """
        Get text encoder for prompt weighting.

        Note: FLUX uses T5 text encoder instead of CLIP.

        Returns:
            Text encoder from pipeline
        """
        if self._pipe and hasattr(self._pipe, "text_encoder"):
            return self._pipe.text_encoder
        return None

    @property
    def use_compel(self) -> bool:
        """
        Compel prompt weighting may not work with FLUX T5 encoder.

        Returns:
            False to disable compel for FLUX
        """
        return False

    def _prepare_pipe_data(self) -> Dict[str, Any]:
        """
        Prepare pipeline initialization parameters with FLUX optimizations.

        This method configures the pipeline with appropriate settings for
        low VRAM usage, including dtype selection, device mapping, and
        4-bit quantization for maximum efficiency.

        Returns:
            Dict of parameters for pipeline initialization
        """
        data = super()._prepare_pipe_data()

        # FLUX works best with bfloat16 on modern GPUs
        data["torch_dtype"] = torch.bfloat16

        # Remove safety checker (FLUX doesn't use it)
        data.pop("safety_checker", None)
        data.pop("feature_extractor", None)

        # Always use 4-bit quantization for maximum VRAM efficiency
        # This leaves more room for ControlNet, img2img, and other features
        quantization_config = self._get_quantization_config()
        if quantization_config:
            data["quantization_config"] = quantization_config
            self.logger.info("4-bit quantization enabled for FLUX model")

        return data

    def _get_quantization_config(self) -> Optional[BitsAndBytesConfig]:
        """
        Get 4-bit quantization configuration for FLUX models.

        Returns:
            BitsAndBytesConfig for 4-bit quantization, or None if unavailable
        """
        try:
            quantization_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_compute_dtype=torch.bfloat16,
                bnb_4bit_use_double_quant=True,  # Nested quantization for extra savings
                bnb_4bit_quant_type="nf4",  # Normal Float 4-bit
            )
            return quantization_config
        except Exception as e:
            self.logger.warning(f"Could not create quantization config: {e}")
            self.logger.warning(
                "Install bitsandbytes for 4-bit quantization: pip install bitsandbytes"
            )
            return None

    def _get_quantized_model_path(self, model_path: str) -> Path:
        """
        Get path where quantized model should be saved.

        Args:
            model_path: Original model path

        Returns:
            Path to quantized model directory
        """
        base_path = Path(model_path)
        parent = base_path.parent
        name = base_path.name

        # Create quantized subdirectory
        quantized_path = parent / f"{name}_4bit_quantized"
        return quantized_path

    def _quantized_model_exists(self, model_path: str) -> bool:
        """
        Check if quantized model already exists on disk.

        Args:
            model_path: Original model path

        Returns:
            True if quantized model exists
        """
        quantized_path = self._get_quantized_model_path(model_path)
        if not quantized_path.exists():
            return False

        # Check for essential files
        essential_files = [
            "config.json",
            "model_index.json",
        ]

        for filename in essential_files:
            if not (quantized_path / filename).exists():
                return False

        # Check for at least one model file (could be safetensors or bin)
        model_files = list(quantized_path.glob("*.safetensors")) + list(
            quantized_path.glob("*.bin")
        )
        if not model_files:
            return False

        self.logger.info(f"Found existing quantized model at {quantized_path}")
        return True

    def _save_quantized_model(self, model_path: str):
        """
        Save quantized model to disk for future use.

        This saves the currently loaded (quantized) pipeline to disk,
        so subsequent loads can skip the quantization step.

        Args:
            model_path: Original model path
        """
        if self._pipe is None:
            self.logger.error("Cannot save quantized model: pipeline is None")
            return

        quantized_path = self._get_quantized_model_path(model_path)

        try:
            self.logger.info(f"Saving quantized model to {quantized_path}")
            self.emit_signal(
                SignalCode.UPDATE_DOWNLOAD_LOG,
                {"message": f"Saving quantized FLUX model to disk..."},
            )

            quantized_path.mkdir(parents=True, exist_ok=True)

            # Save the pipeline
            self._pipe.save_pretrained(
                str(quantized_path),
                safe_serialization=True,
            )

            self.logger.info("Quantized model saved successfully")
            self.emit_signal(
                SignalCode.UPDATE_DOWNLOAD_LOG,
                {"message": f"✓ Quantized model saved to {quantized_path}"},
            )

        except Exception as e:
            self.logger.error(f"Failed to save quantized model: {e}")
            self.emit_signal(
                SignalCode.UPDATE_DOWNLOAD_LOG,
                {"message": f"⚠ Failed to save quantized model: {e}"},
            )

    def _set_pipe(self, config_path: str, data: Dict):
        """
        Load FLUX pipeline with automatic quantization.

        This method implements the quantization workflow:
        1. Check if quantized model exists on disk → load it
        2. If not, load full model with quantization config
        3. Save quantized model to disk for future use

        Args:
            config_path: Path to model config
            data: Pipeline initialization parameters
        """
        pipeline_class = self._pipeline_class
        model_path = self.model_path

        # Check if quantized version exists
        if self._quantized_model_exists(model_path):
            quantized_path = self._get_quantized_model_path(model_path)
            self.logger.info(
                f"Loading quantized FLUX model from {quantized_path}"
            )

            try:
                # Load from quantized path
                self._pipe = pipeline_class.from_pretrained(
                    str(quantized_path),
                    **data,
                )
                self.logger.info("✓ Loaded quantized model from disk")
                return

            except Exception as e:
                self.logger.warning(f"Failed to load quantized model: {e}")
                self.logger.info(
                    "Falling back to full model with runtime quantization"
                )

        # Load full model with quantization (will quantize at runtime)
        self.logger.info(
            f"Loading FLUX model with 4-bit quantization: {model_path}"
        )
        self.emit_signal(
            SignalCode.UPDATE_DOWNLOAD_LOG,
            {
                "message": "Loading FLUX model with 4-bit quantization (this may take a moment)..."
            },
        )

        try:
            if self.use_from_single_file:
                self._pipe = pipeline_class.from_single_file(
                    model_path,
                    config=config_path,
                    add_watermarker=False,
                    **data,
                )
            else:
                file_directory = (
                    os.path.dirname(model_path)
                    if os.path.isfile(model_path)
                    else model_path
                )
                self._pipe = pipeline_class.from_pretrained(
                    file_directory,
                    config=config_path,
                    **data,
                )

            self.logger.info("✓ Model loaded with 4-bit quantization")

            # Save quantized model for future use
            self._save_quantized_model(model_path)

        except Exception as e:
            self.logger.error(f"Failed to load FLUX model: {e}")
            raise

    def _make_memory_efficient(self):
        """
        Apply memory optimizations for low VRAM systems.

        This method applies several optimizations:
        1. Enable model CPU offload (moves layers between CPU/GPU)
        2. Enable VAE slicing (processes images in tiles)
        3. Enable attention slicing (reduces memory during attention)
        4. Optional: Sequential CPU offload for minimal VRAM

        The optimizations are applied progressively based on available VRAM.
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
            self.logger.error(f"Failed to apply memory optimizations: {e}")

    def _get_vram_gb(self) -> float:
        """Get available VRAM in GB."""
        total_vram = torch.cuda.get_device_properties(0).total_memory
        return total_vram / (1024**3)

    def _apply_vram_optimizations(self, vram_gb: float):
        """Apply CPU offload based on VRAM availability."""
        self.logger.info(f"Detected {vram_gb:.1f}GB VRAM")

        if vram_gb < 24:
            self.logger.info("Enabling model CPU offload for low VRAM")
            self._pipe.enable_model_cpu_offload()
        else:
            self.logger.info("Loading full model to GPU")
            self._pipe.to(self._device)

        if vram_gb < 16:
            self.logger.info("Enabling sequential CPU offload")
            self._pipe.enable_sequential_cpu_offload()

    def _enable_slicing_optimizations(self):
        """Enable VAE and attention slicing."""
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
        self._memory_settings_flags["vae_slicing"] = True
        self._memory_settings_flags["attention_slicing"] = True

    def _load_prompt_embeds(self):
        """
        Load and prepare prompt embeddings for FLUX.

        FLUX uses T5 embeddings which are handled differently than
        CLIP embeddings in Stable Diffusion. This method prepares
        the prompts but doesn't use Compel weighting.
        """
        # FLUX handles prompts differently - no Compel weighting
        # Just store the prompts as-is
        self._current_prompt = self.prompt
        self._current_negative_prompt = self.negative_prompt

        # FLUX doesn't use pre-computed embeddings in the same way
        # The pipeline handles this internally
        self.logger.debug("FLUX prompt handling (no pre-computed embeddings)")

    def _clear_memory_efficient_settings(self):
        """
        Clear memory optimization flags and disable optimizations.

        This is called when switching pipelines or unloading models.
        """
        if self._pipe is not None:
            try:
                if hasattr(self._pipe, "disable_vae_slicing"):
                    self._pipe.disable_vae_slicing()
                if hasattr(self._pipe, "disable_attention_slicing"):
                    self._pipe.disable_attention_slicing()
            except Exception as e:
                self.logger.debug(f"Error clearing memory settings: {e}")

        super()._clear_memory_efficient_settings()

    def load_model(self, *args, **kwargs) -> None:
        """
        Load FLUX model (interface method).

        Args:
            *args: Positional arguments
            **kwargs: Keyword arguments
        """
        return self._load_model(*args, **kwargs)

    def unload_model(self, *args, **kwargs) -> None:
        """
        Unload FLUX model (interface method).

        Args:
            *args: Positional arguments
            **kwargs: Keyword arguments
        """
        return self._unload_model(*args, **kwargs)

    def _load_model(self, *args, **kwargs):
        """
        Internal method to load FLUX model.

        This uses the standard load() method from BaseDiffusersModelManager
        which handles all the loading logic.
        """
        self.load()

    def _unload_model(self, *args, **kwargs):
        """
        Internal method to unload FLUX model.

        This uses the standard unload() method from BaseDiffusersModelManager
        which handles all the unloading logic.
        """
        self.unload()
