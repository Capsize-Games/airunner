from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional, List

from airunner.settings import AIRUNNER_LOG_LEVEL
from airunner.utils.application import get_logger


class ModelProvider(Enum):
    """Supported model providers."""

    MISTRAL = "mistral"
    LLAMA = "llama"
    STABLE_DIFFUSION = "stable_diffusion"
    HUNYUAN = "hunyuan"
    WHISPER = "whisper"
    BARK = "bark"


class ModelType(Enum):
    """Model type categories."""

    LLM = "llm"
    TEXT_TO_IMAGE = "text_to_image"
    TEXT_TO_SPEECH = "text_to_speech"
    SPEECH_TO_TEXT = "speech_to_text"
    TEXT_TO_VIDEO = "text_to_video"


@dataclass
class ModelMetadata:
    """Metadata for a specific model."""

    name: str
    provider: ModelProvider
    model_type: ModelType
    size_gb: float
    min_vram_gb: float
    min_ram_gb: float
    recommended_vram_gb: float
    recommended_ram_gb: float
    supports_quantization: bool
    huggingface_id: str
    compute_capability_min: Optional[tuple] = None


class ModelRegistry:
    """Registry of supported models with hardware requirements."""

    def __init__(self):
        self.logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)
        self._models: Dict[str, ModelMetadata] = {}
        self._initialize_registry()

    def _initialize_registry(self) -> None:
        """Initialize the model registry with known models."""
        self._register_mistral_models()
        self._register_llama_models()
        self._register_stable_diffusion_models()
        self._register_tts_models()
        self._register_stt_models()

    def _register_mistral_models(self) -> None:
        """Register Mistral AI models."""
        models = [
            ModelMetadata(
                name="Ministral 3 8B",
                provider=ModelProvider.MISTRAL,
                model_type=ModelType.LLM,
                size_gb=10.4,
                min_vram_gb=8.0,
                min_ram_gb=12.0,
                recommended_vram_gb=12.0,
                recommended_ram_gb=16.0,
                supports_quantization=True,
                huggingface_id="mistralai/Ministral-3-8B-Instruct-2512",
            ),
        ]

        for model in models:
            self._models[model.huggingface_id] = model

    def _register_llama_models(self) -> None:
        """Register Llama models.
        
        NOTE: Meta Llama 3.1 8B removed - outdated compared to Qwen3/Ministral3.
        Llama 3.3 is 70B only (too large for most users).
        Meta does NOT have a thinking model equivalent.
        """
        # No Llama models currently recommended - Qwen3-8B is superior
        pass

    def _register_stable_diffusion_models(self) -> None:
        """Register Stable Diffusion models.
        """
        models = [
            ModelMetadata(
                name="Stable Diffusion XL 1.0",
                provider=ModelProvider.STABLE_DIFFUSION,
                model_type=ModelType.TEXT_TO_IMAGE,
                size_gb=6.9,
                min_vram_gb=6.0,
                min_ram_gb=8.0,
                recommended_vram_gb=8.0,
                recommended_ram_gb=16.0,
                supports_quantization=False,
                huggingface_id="stabilityai/stable-diffusion-xl-base-1.0",
            ),
        ]

        for model in models:
            self._models[model.huggingface_id] = model

    def _register_tts_models(self) -> None:
        """Register Text-to-Speech models."""
        models = [
            ModelMetadata(
                name="Bark",
                provider=ModelProvider.BARK,
                model_type=ModelType.TEXT_TO_SPEECH,
                size_gb=5.0,
                min_vram_gb=4.0,
                min_ram_gb=8.0,
                recommended_vram_gb=6.0,
                recommended_ram_gb=16.0,
                supports_quantization=False,
                huggingface_id="suno/bark",
            ),
        ]

        for model in models:
            self._models[model.huggingface_id] = model

    def _register_stt_models(self) -> None:
        """Register Speech-to-Text models."""
        models = [
            ModelMetadata(
                name="Whisper Large V3",
                provider=ModelProvider.WHISPER,
                model_type=ModelType.SPEECH_TO_TEXT,
                size_gb=3.1,
                min_vram_gb=4.0,
                min_ram_gb=8.0,
                recommended_vram_gb=6.0,
                recommended_ram_gb=16.0,
                supports_quantization=True,
                huggingface_id="openai/whisper-large-v3",
            ),
        ]

        for model in models:
            self._models[model.huggingface_id] = model

    def get_model(self, model_id: str) -> Optional[ModelMetadata]:
        """Get model metadata by ID."""
        return self._models.get(model_id)

    def list_models(
        self,
        provider: Optional[ModelProvider] = None,
        model_type: Optional[ModelType] = None,
    ) -> List[ModelMetadata]:
        """List models with optional filters."""
        models = list(self._models.values())

        if provider:
            models = [m for m in models if m.provider == provider]
        if model_type:
            models = [m for m in models if m.model_type == model_type]

        return models

    def register_model(self, metadata: ModelMetadata) -> None:
        """Register a new model."""
        self._models[metadata.huggingface_id] = metadata
        self.logger.info(f"Registered model: {metadata.name}")
