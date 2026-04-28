from typing import Any, List, Optional

from transformers import (
    AutoModelForCausalLM,
)
from transformers.generation.streamers import TextIteratorStreamer

from airunner.components.conversations.conversation_history_manager import (
    ConversationHistoryManager,
)
from airunner.components.application.managers.base_model_manager import (
    BaseModelManager,
)
from airunner.components.llm.managers.tool_manager import ToolManager
from airunner.components.llm.managers.workflow_manager import WorkflowManager
from airunner.components.llm.managers.quantization_mixin import (
    QuantizationMixin,
)
from airunner.components.llm.managers.mixins import (
    AdapterLoaderMixin,
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
from airunner.components.llm.managers.training_mixin import TrainingMixin
from airunner.components.llm.managers.agent.rag_mixin import RAGMixin
from airunner.components.model_management.model_resource_manager import (
    ModelResourceManager,
)
from airunner.enums import (
    ModelType,
    ModelStatus,
)
from airunner.utils.memory import clear_memory
from airunner.components.llm.managers.llm_settings import LLMSettings


class LLMModelManager(
    BaseModelManager,
    AdapterLoaderMixin,
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
    TrainingMixin,
):
    """
    Handler for Large Language Model operations in AI Runner.

    This class manages the lifecycle of LLM models, including loading, unloading,
    and generating responses. It supports local HuggingFace models, OpenRouter,
    Ollama, and OpenAI (future) through LangChain/LangGraph integration.

    Attributes:
        model_type: Type of model being handled (LLM).
        model_class: String identifier for the model class.
        llm_settings: Settings for LLM configuration.
    """

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

    llm_settings: LLMSettings

    def __init__(
        self,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        # Explicitly initialize RAGMixin since it's in the inheritance chain
        # This ensures all private attributes (_retriever, _embedding, etc.) are created
        self.llm_request: Optional[Any] = None
        RAGMixin.__init__(self)
        self._model_status = {ModelType.LLM: ModelStatus.UNLOADED}
        self.llm_settings = LLMSettings()
        self._pending_conversation_message = None
        self._conversation_history_manager = ConversationHistoryManager()
        self._current_model_path = None
        self._hw_profiler = None
        self._current_request_id = None

    def _load_local_llm_components(self) -> None:
        """Load tokenizer and model for local LLM.
        
        For GGUF models, we skip loading the HuggingFace model and tokenizer
        since ChatLlamaCpp (via ChatGGUF) handles everything internally.
        """
        if self.llm_settings.use_local_llm:
            # Check if this is a GGUF model - if so, skip HF loading
            from airunner.components.llm.adapters import is_gguf_model
            if is_gguf_model(self.model_path):
                self.logger.info(
                    f"GGUF model detected at {self.model_path}, "
                    "skipping HuggingFace model/tokenizer loading"
                )
                return
            self._load_tokenizer()
            self._load_model()

    def load(self) -> None:
        """Load the LLM model and its supporting orchestration components."""
        self.logger.info(
            "load() called, current status: %s",
            self.model_status[ModelType.LLM],
        )
        if self.model_status[ModelType.LLM] in (
            ModelStatus.LOADING,
            ModelStatus.LOADED,
        ):
            self.logger.info(
                "Returning early - model already in state: %s",
                self.model_status[ModelType.LLM],
            )
            return

        if not self._validate_model_path():
            return

        if not self._check_and_download_model():
            return

        self.change_model_status(ModelType.LLM, ModelStatus.LOADING)
        self.unload()
        self._current_model_path = self.model_path

        resource_manager = ModelResourceManager()
        prepare_result = resource_manager.prepare_model_loading(
            model_id=self.model_path,
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
            "[LLM LOAD] Chat model loaded: %s",
            self._chat_model is not None,
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
        resource_manager.model_loaded(self.model_path)

    def unload(self) -> None:
        """Unload all LLM components and clear reserved resources."""
        if self.model_status[ModelType.LLM] in (
            ModelStatus.LOADING,
            ModelStatus.UNLOADED,
        ):
            return

        self.change_model_status(ModelType.LLM, ModelStatus.LOADING)
        self._unload_components()

        resource_manager = ModelResourceManager()
        resource_manager.cleanup_model(
            model_id=self._current_model_path or self.model_path,
            model_type="llm",
        )

        clear_memory(self.device)
        self.change_model_status(ModelType.LLM, ModelStatus.UNLOADED)

    # Specialized model methods
