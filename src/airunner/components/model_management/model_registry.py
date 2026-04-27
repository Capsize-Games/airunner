from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional

from airunner.settings import AIRUNNER_LOG_LEVEL
from airunner.utils.application import get_logger


class ModelProvider(Enum):
    """Supported model providers."""

    MISTRAL = "mistral"
    QWEN = "qwen"
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
    model_id: Optional[str] = None
    preferred_runtime_format: Optional[str] = None
    preferred_download_repo_id: Optional[str] = None
    preferred_download_filename: Optional[str] = None
    runtime_backend: Optional[str] = None
    compute_capability_min: Optional[tuple] = None

    @property
    def size_mb(self) -> int:
        """Return approximate model size in megabytes."""
        return int(self.size_gb * 1024)


class ModelRegistry:
    """Registry of supported models with hardware requirements."""

    def __init__(self):
        self.logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)
        self._models: Dict[str, ModelMetadata] = {}
        self._aliases: Dict[str, str] = {}
        self._initialize_registry()

    @property
    def models(self) -> Dict[str, ModelMetadata]:
        """Return canonical registry entries keyed by model identifier."""
        return dict(self._models)

    def _initialize_registry(self) -> None:
        """Initialize the model registry with known models."""
        self._register_llm_models()
        self._register_stable_diffusion_models()
        self._register_tts_models()
        self._register_stt_models()

    def _register_llm_models(self) -> None:
        """Register local LLM models from the GGUF-aware provider catalog."""
        from airunner.components.llm.config.provider_config import (
            LLMProviderConfig,
        )

        for model_id, model_info in LLMProviderConfig.LOCAL_MODELS.items():
            if model_id == "custom":
                continue
            self._register_model_metadata(
                self._build_llm_metadata(model_id, model_info)
            )

    def _build_llm_metadata(
        self,
        model_id: str,
        model_info: Dict[str, object],
    ) -> ModelMetadata:
        """Build one registry entry for a local LLM model."""
        preferred_download = self._preferred_llm_download(model_id)
        runtime_format = "transformers"
        runtime_backend = "transformers"
        preferred_repo_id = str(model_info.get("repo_id", ""))
        preferred_filename = None
        if preferred_download and preferred_download.get("model_type") == "gguf":
            runtime_format = "gguf"
            runtime_backend = "llama.cpp"
            preferred_repo_id = str(preferred_download.get("repo_id", preferred_repo_id))
            preferred_filename = preferred_download.get("gguf_filename")

        min_vram_gb = float(
            model_info.get("vram_4bit_gb")
            or model_info.get("vram_8bit_gb")
            or 4.0
        )
        recommended_vram_gb = float(
            model_info.get("vram_8bit_gb")
            or model_info.get("vram_4bit_gb")
            or min_vram_gb
        )
        size_gb = min_vram_gb if runtime_format == "gguf" else recommended_vram_gb

        return ModelMetadata(
            name=str(model_info.get("name", model_id)),
            provider=self._llm_provider(model_id, preferred_repo_id),
            model_type=ModelType.LLM,
            size_gb=size_gb,
            min_vram_gb=min_vram_gb,
            min_ram_gb=max(min_vram_gb * 1.5, 8.0),
            recommended_vram_gb=max(recommended_vram_gb, min_vram_gb),
            recommended_ram_gb=max(recommended_vram_gb * 1.5, 12.0),
            supports_quantization=bool(
                model_info.get("gguf_repo_id") or model_info.get("vram_4bit_gb")
            ),
            huggingface_id=str(model_info.get("repo_id", "")),
            model_id=model_id,
            preferred_runtime_format=runtime_format,
            preferred_download_repo_id=preferred_repo_id,
            preferred_download_filename=preferred_filename,
            runtime_backend=runtime_backend,
        )

    @staticmethod
    def _llm_provider(model_id: str, repo_id: str) -> ModelProvider:
        """Return the provider enum that best matches one local LLM model."""
        owner = str(repo_id).split("/", 1)[0].strip().lower()
        if owner == "mistralai" or "ministral" in model_id:
            return ModelProvider.MISTRAL
        if owner == "qwen" or "qwen" in model_id:
            return ModelProvider.QWEN
        return ModelProvider.LLAMA

    @staticmethod
    def _preferred_llm_download(model_id: str) -> Optional[Dict[str, object]]:
        """Return the preferred downloadable artifact for one local LLM."""
        from airunner.components.llm.config.provider_config import (
            LLMProviderConfig,
        )

        return LLMProviderConfig.resolve_download_target(
            "local",
            model_id=model_id,
            prefer_pre_quantized=True,
        )

    def _register_model_metadata(self, metadata: ModelMetadata) -> None:
        """Register one model along with compatible lookup aliases."""
        canonical_id = metadata.model_id or metadata.huggingface_id
        self._models[canonical_id] = metadata
        for alias in (
            canonical_id,
            metadata.huggingface_id,
            metadata.preferred_download_repo_id,
        ):
            if alias:
                self._aliases[alias] = canonical_id

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
            self._register_model_metadata(model)

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
            self._register_model_metadata(model)

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
            self._register_model_metadata(model)

    def get_model(self, model_id: str) -> Optional[ModelMetadata]:
        """Get model metadata by ID."""
        canonical_id = self._aliases.get(model_id, model_id)
        return self._models.get(canonical_id)

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
        self._register_model_metadata(metadata)
        self.logger.info(f"Registered model: {metadata.name}")
