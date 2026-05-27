"""Model registry helpers for model resource management."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from importlib import import_module


class ModelProvider(Enum):
	"""Supported model providers."""

	MISTRAL = "mistral"
	OPENAI = "openai"
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
	"""Metadata for one model."""

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
	model_id: str | None = None
	preferred_runtime_format: str | None = None
	preferred_download_repo_id: str | None = None
	preferred_download_filename: str | None = None
	runtime_backend: str | None = None
	aliases: tuple[str, ...] = ()
	compute_capability_min: tuple[int, int] | None = None

	@property
	def size_mb(self) -> int:
		"""Return approximate model size in megabytes."""
		return int(self.size_gb * 1024)


def _load_provider_config() -> type | None:
	"""Load the legacy provider catalog when it is available."""
	try:
		module = import_module("airunner_model.llm.provider_config")
		return module.LLMProviderConfig
	except Exception:
		return None


class ModelRegistry:
	"""Registry of supported models with hardware requirements."""

	def __init__(self) -> None:
		self.logger = logging.getLogger(__name__)
		self._models: dict[str, ModelMetadata] = {}
		self._aliases: dict[str, str] = {}
		self._initialize_registry()

	@property
	def models(self) -> dict[str, ModelMetadata]:
		"""Return canonical registry entries keyed by model identifier."""
		return dict(self._models)

	def _initialize_registry(self) -> None:
		self._register_llm_models()
		self._register_stable_diffusion_models()
		self._register_tts_models()
		self._register_stt_models()

	def _register_llm_models(self) -> None:
		provider_config = _load_provider_config()
		if provider_config is None:
			return
		for model_id, model_info in provider_config.LOCAL_MODELS.items():
			if model_id == "custom":
				continue
			metadata = self._build_llm_metadata(
				model_id,
				model_info,
				provider_config,
			)
			self._register_model_metadata(metadata)

	def _build_llm_metadata(
		self,
		model_id: str,
		model_info: dict[str, object],
		provider_config: type,
	) -> ModelMetadata:
		preferred_download = self._preferred_llm_download(
			model_id,
			provider_config,
		)
		runtime_format = "transformers"
		runtime_backend = "transformers"
		preferred_repo_id = str(model_info.get("repo_id", ""))
		preferred_filename = None
		if preferred_download and preferred_download.get("model_type") == "gguf":
			runtime_format = "gguf"
			runtime_backend = "llama.cpp"
			preferred_repo_id = str(
				preferred_download.get("repo_id", preferred_repo_id)
			)
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
		size_gb = (
			min_vram_gb if runtime_format == "gguf" else recommended_vram_gb
		)
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
				model_info.get("gguf_repo_id")
				or model_info.get("vram_4bit_gb")
			),
			huggingface_id=str(model_info.get("repo_id", "")),
			model_id=model_id,
			preferred_runtime_format=runtime_format,
			preferred_download_repo_id=preferred_repo_id,
			preferred_download_filename=preferred_filename,
			runtime_backend=runtime_backend,
			aliases=self._llm_aliases(model_info),
		)

	@staticmethod
	def _llm_provider(model_id: str, repo_id: str) -> ModelProvider:
		"""Return the provider enum that best matches one local LLM."""
		owner = str(repo_id).split("/", 1)[0].strip().lower()
		if owner == "mistralai":
			return ModelProvider.MISTRAL
		if owner == "openai" or "gpt-oss" in model_id:
			return ModelProvider.OPENAI
		if owner == "qwen" or "qwen" in model_id:
			return ModelProvider.QWEN
		return ModelProvider.LLAMA

	@staticmethod
	def _preferred_llm_download(
		model_id: str,
		provider_config: type,
	) -> dict[str, object] | None:
		"""Return the preferred downloadable artifact for one local LLM."""
		return provider_config.resolve_download_target(
			"local",
			model_id=model_id,
			prefer_pre_quantized=True,
		)

	@staticmethod
	def _normalize_alias(alias: str) -> str:
		"""Normalize one registry alias for case-insensitive lookups."""
		return "".join(
			character
			for character in str(alias or "").lower()
			if character.isalnum()
		)

	@staticmethod
	def _llm_aliases(model_info: dict[str, object]) -> tuple[str, ...]:
		"""Return stable aliases for one local LLM registry entry."""
		aliases = list(model_info.get("aliases", []))
		for key in ("name", "gguf_filename"):
			value = model_info.get(key)
			if value:
				aliases.append(str(value))
		return tuple(dict.fromkeys(alias for alias in aliases if alias))

	def _register_alias(self, alias: str, canonical_id: str) -> None:
		"""Register one exact and normalized alias for model lookup."""
		if not alias:
			return
		self._aliases[alias] = canonical_id
		normalized = self._normalize_alias(alias)
		if normalized:
			self._aliases[normalized] = canonical_id

	def _register_model_metadata(self, metadata: ModelMetadata) -> None:
		"""Register one model along with compatible lookup aliases."""
		canonical_id = metadata.model_id or metadata.huggingface_id
		self._models[canonical_id] = metadata
		for alias in (
			canonical_id,
			metadata.name,
			metadata.huggingface_id,
			metadata.preferred_download_repo_id,
			metadata.preferred_download_filename,
			*metadata.aliases,
		):
			self._register_alias(str(alias), canonical_id)

	def _register_stable_diffusion_models(self) -> None:
		metadata = ModelMetadata(
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
		)
		self._register_model_metadata(metadata)

	def _register_tts_models(self) -> None:
		metadata = ModelMetadata(
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
		)
		self._register_model_metadata(metadata)

	def _register_stt_models(self) -> None:
		metadata = ModelMetadata(
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
			preferred_runtime_format="ggml",
			preferred_download_repo_id="ggerganov/whisper.cpp",
			preferred_download_filename="ggml-large-v3.bin",
			runtime_backend="whisper.cpp",
		)
		self._register_model_metadata(metadata)

	def get_model(self, model_id: str) -> ModelMetadata | None:
		"""Return model metadata by ID or alias."""
		canonical_id = self._aliases.get(model_id)
		if canonical_id is None:
			canonical_id = self._aliases.get(
				self._normalize_alias(model_id),
				model_id,
			)
		return self._models.get(canonical_id)

	def list_models(
		self,
		provider: ModelProvider | None = None,
		model_type: ModelType | None = None,
	) -> list[ModelMetadata]:
		"""List models with optional filters."""
		models = list(self._models.values())
		if provider:
			models = [model for model in models if model.provider == provider]
		if model_type:
			models = [model for model in models if model.model_type == model_type]
		return models

	def register_model(self, metadata: ModelMetadata) -> None:
		"""Register a new model."""
		self._register_model_metadata(metadata)
		self.logger.info("Registered model: %s", metadata.name)