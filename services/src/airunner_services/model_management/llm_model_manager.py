"""Service-owned top-level LLM model manager."""

import os

from typing import Any, List, Optional

from transformers import AutoModelForCausalLM
from transformers.generation.streamers import TextIteratorStreamer


from airunner_services.model_management.base_model_manager import (
	BaseModelManager,
)
from airunner_services.llm.llm_settings import LLMSettings
from airunner_services.llm.quantization_mixin import QuantizationMixin
from airunner_services.llm.rag_mixin import RAGMixin
from airunner_services.llm.tool_manager import ToolManager
from airunner_services.llm.workflow_manager import WorkflowManager
from airunner_services.llm.managers.mixins import (
	BatchProcessingMixin,
	ComponentLoaderMixin,
	ConversationManagementMixin,
	GenerationMixin,
	ModelAvailabilityMixin,
	ModelLoaderMixin,
	PropertyMixin,
	QuantizationConfigMixin,
	RequestHandlingMixin,
	SpecializedModelMixin,
	StatusManagementMixin,
	SystemPromptMixin,
	TokenizerLoaderMixin,
	ToolClassificationMixin,
	ToolFilteringMixin,
	ValidationMixin,
)
from airunner_services.contract_enums import ModelStatus, ModelType
from airunner_services.conversations.conversation_history_manager import (
	ConversationHistoryManager,
)
from airunner_services.llm.config.provider_config import LLMProviderConfig
from airunner_services.model_management import ModelResourceManager
from airunner_services.utils.memory import apply_cudnn_benchmark
from airunner_services.utils.memory.clear_memory import clear_memory


class LLMModelManager(
	BaseModelManager,
	BatchProcessingMixin,
	ComponentLoaderMixin,
	ConversationManagementMixin,
	GenerationMixin,
	ModelAvailabilityMixin,
	ModelLoaderMixin,
	PropertyMixin,
	QuantizationConfigMixin,
	RequestHandlingMixin,
	SpecializedModelMixin,
	StatusManagementMixin,
	SystemPromptMixin,
	TokenizerLoaderMixin,
	ToolClassificationMixin,
	ToolFilteringMixin,
	ValidationMixin,
	RAGMixin,
	QuantizationMixin,
):
	"""Handle LLM model lifecycle and orchestration."""

	model_type: ModelType = ModelType.LLM
	model_class: str = "llm"

	_model: Optional[AutoModelForCausalLM] = None
	_streamer: Optional[TextIteratorStreamer] = None
	_tokenizer: Optional[object] = None
	_current_model_path: Optional[str] = None

	_chat_model: Optional[Any] = None
	_tool_manager: Optional[ToolManager] = None
	_workflow_manager: Optional[WorkflowManager] = None

	_history: Optional[List] = []
	_interrupted: bool = False
	_current_request_id: Optional[str] = None
	_last_load_error: Optional[str] = None

	llm_settings: LLMSettings

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.llm_request: Optional[Any] = None
		RAGMixin.__init__(self)
		self._model_status = {ModelType.LLM: ModelStatus.UNLOADED}
		self.llm_settings = LLMSettings()
		self._pending_conversation_message = None
		self._conversation_history_manager = ConversationHistoryManager()
		self._current_model_path = None
		self._hw_profiler = None
		self._current_request_id = None
		self._last_load_error = None
		apply_cudnn_benchmark(self.memory_settings)

	def _load_local_llm_components(self) -> None:
		"""Load tokenizer and model for local LLM when needed."""
		if self.llm_settings.use_local_llm:
			from airunner_services.llm.adapters import is_gguf_model

			if is_gguf_model(self.model_path):
				self.logger.info(
					"GGUF model detected at %s, skipping manager-side "
					"tokenizer/model loading",
					self.model_path,
				)
				return

			self.logger.info(
				"Skipping manager-side local model loading for non-GGUF path "
				"%s; local LLM mode now requires GGUF/llama.cpp.",
				self.model_path,
			)

	def load(self) -> None:
		"""Load the LLM model and its supporting orchestration components."""
		current_status = self.model_status[ModelType.LLM]
		self.logger.info(
			"load() called, current status: %s",
			current_status,
		)
		apply_cudnn_benchmark(self.memory_settings)

		self._last_load_error = None
		if not self._validate_model_path():
			return
		if not self._check_and_download_model():
			return

		target_model_path = self.model_path
		target_model_id = self._resolve_model_id_from_path(target_model_path)
		target_model_name = self._resolve_model_name(target_model_id)

		if current_status is ModelStatus.LOADING:
			self.logger.info(
				"Returning early - model is already loading "
				"(model_id=%s, model_name=%s)",
				target_model_id or "unknown",
				target_model_name or "unknown",
			)
			return

		if current_status is ModelStatus.LOADED:
			if self._current_model_path == target_model_path:
				self.logger.info(
					"Returning early - requested model already loaded "
					"(model_id=%s, model_name=%s)",
					target_model_id or "unknown",
					target_model_name or "unknown",
				)
				return

			current_model_id = self._resolve_model_id_from_path(
				self._current_model_path,
			)
			current_model_name = self._resolve_model_name(current_model_id)
			self.logger.info(
				"[LLM LOAD] Switching models: %s (%s) -> %s (%s)",
				current_model_id or "unknown",
				current_model_name or "unknown",
				target_model_id or "unknown",
				target_model_name or "unknown",
			)
			self.unload()

		self.change_model_status(ModelType.LLM, ModelStatus.LOADING)
		self._current_model_path = target_model_path
		self.logger.info(
			"[LLM LOAD] Resolved model path: %s (model_id=%s, model_name=%s)",
			self._current_model_path,
			target_model_id or "unknown",
			target_model_name or "unknown",
		)

		resource_manager = ModelResourceManager()
		prepare_result = resource_manager.prepare_model_loading(
			model_id=self._current_model_path,
			model_type="llm",
		)
		if not prepare_result["can_load"]:
			self.logger.error(
				"Cannot load model: %s",
				prepare_result.get("reason", "Unknown reason"),
			)
			self.change_model_status(ModelType.LLM, ModelStatus.FAILED)
			self.logger.info(
				"[LLM LOAD] Model cannot be loaded - resource conflict"
			)
			return

		if self.llm_settings.use_local_llm:
			self._send_quantization_info()

		self._load_local_llm_components()
		self._load_chat_model()
		self.logger.info(
			"[LLM LOAD] Chat model loaded: %s (model_id=%s, model_name=%s, model_path=%s)",
			self._chat_model is not None,
			target_model_id or "unknown",
			target_model_name or "unknown",
			self._current_model_path,
		)
		self._load_tool_manager()
		self.logger.info(
			"[LLM LOAD] Tool manager loaded: %s",
			self._tool_manager is not None,
		)
		self._load_workflow_manager()
		self.logger.info(
			"[LLM LOAD] Workflow manager loaded: %s",
			self._workflow_manager is not None,
		)
		self._update_model_status()
		self.logger.info(
			"[LLM LOAD] Model status updated to: %s",
			self.model_status[ModelType.LLM],
		)
		resource_manager.model_loaded(self._current_model_path)

	def _resolve_model_id_from_path(
		self,
		model_path: Optional[str],
	) -> str:
		"""Return the configured local model id for one resolved model path."""
		if model_path:
			resolved = LLMProviderConfig.resolve_model_id(
				"local",
				os.path.basename(str(model_path)),
			)
			if resolved:
				return resolved

		return LLMProviderConfig.resolve_model_id(
			"local",
			getattr(self.llm_generator_settings, "model_id", "") or "",
		)

	def _resolve_model_name(self, model_id: str) -> str:
		"""Return the display name for one configured local model id."""
		if not model_id:
			return ""
		model_info = LLMProviderConfig.get_model_info("local", model_id)
		return str(model_info.get("name", "") or model_id)

	def unload(self) -> None:
		"""Unload all LLM components and clear reserved resources."""
		if self.model_status[ModelType.LLM] in (
			ModelStatus.LOADING,
			ModelStatus.UNLOADED,
		):
			return

		current_model_id = self._resolve_model_id_from_path(
			self._current_model_path,
		)
		current_model_name = self._resolve_model_name(current_model_id)
		self.logger.info(
			"[LLM UNLOAD] Unloading model_id=%s model_name=%s model_path=%s",
			current_model_id or "unknown",
			current_model_name or "unknown",
			self._current_model_path or self.model_path,
		)

		self._last_load_error = None
		self.change_model_status(ModelType.LLM, ModelStatus.LOADING)
		self._unload_components()

		resource_manager = ModelResourceManager()
		resource_manager.cleanup_model(
			model_id=self._current_model_path or self.model_path,
			model_type="llm",
		)
		clear_memory(self.device)
		self._current_model_path = None
		self.change_model_status(ModelType.LLM, ModelStatus.UNLOADED)