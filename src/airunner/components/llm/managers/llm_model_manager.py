from typing import Optional, Dict, Any, List

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
    ComponentLoaderMixin,
    ConversationManagementMixin,
    GenerationMixin,
    ModelLoaderMixin,
    PropertyMixin,
    QuantizationConfigMixin,
    SpecializedModelMixin,
    StatusManagementMixin,
    SystemPromptMixin,
    TokenizerLoaderMixin,
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
    ComponentLoaderMixin,
    ConversationManagementMixin,
    GenerationMixin,
    ModelLoaderMixin,
    PropertyMixin,
    QuantizationConfigMixin,
    SpecializedModelMixin,
    StatusManagementMixin,
    SystemPromptMixin,
    TokenizerLoaderMixin,
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

    llm_settings: LLMSettings

    def __init__(
        self,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        # Explicitly initialize RAGMixin since it's in the inheritance chain
        # This ensures all private attributes (_retriever, _embedding, etc.) are created
        RAGMixin.__init__(self)
        self._model_status = {ModelType.LLM: ModelStatus.UNLOADED}
        self.llm_settings = LLMSettings()
        self._pending_conversation_message = None
        self._conversation_history_manager = ConversationHistoryManager()
        self._current_model_path = None
        self._hw_profiler = None

    def _load_local_llm_components(self) -> None:
        """Load tokenizer and model for local LLM."""
        if self.llm_settings.use_local_llm:
            self._load_tokenizer()
            self._load_model()

    def load(self) -> None:
        """
        Load the LLM model and associated components.

        This method handles the complete loading process, including:
        - Validating model path is configured
        - Checking if model exists (trigger download if needed)
        - Checking if the model is already loaded
        - Loading the tokenizer and model (for local LLM)
        - Creating the appropriate ChatModel via factory
        - Loading the tool manager
        - Loading the workflow manager
        - Updating the model status based on loading results
        """
        if self.model_status[ModelType.LLM] in (
            ModelStatus.LOADING,
            ModelStatus.LOADED,
        ):
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
                f"Cannot load model: {prepare_result.get('reason', 'Unknown reason')}"
            )
            self.change_model_status(ModelType.LLM, ModelStatus.FAILED)
            return

        if self.llm_settings.use_local_llm:
            self._send_quantization_info()

        self._load_local_llm_components()
        self._load_chat_model()
        self._load_tool_manager()
        self._load_workflow_manager()
        self._update_model_status()

        # Mark model as loaded
        resource_manager.model_loaded(self.model_path)

    def unload(self) -> None:
        """Unload all LLM components and clear GPU memory."""
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

    def handle_request(
        self,
        data: Dict,
        extra_context: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Handle an incoming request for LLM generation."""
        self.logger.info(f"handle_request called on instance {id(self)}")

        # CRITICAL: Clear ALL interrupt flags at the start of a new request
        # This ensures that a new user message can be processed even if
        # the previous generation was interrupted
        self._interrupted = False
        if self._chat_model and hasattr(self._chat_model, "set_interrupted"):
            self._chat_model.set_interrupted(False)
        if self._workflow_manager and hasattr(
            self._workflow_manager, "set_interrupted"
        ):
            self._workflow_manager.set_interrupted(False)

        self._do_set_seed()
        self.load()

        return self._do_generate(
            prompt=data["request_data"]["prompt"],
            action=data["request_data"]["action"],
            llm_request=data["request_data"]["llm_request"],
            extra_context=extra_context,
        )

    def do_interrupt(self) -> None:
        """Interrupt ongoing generation."""
        self.logger.info(f"do_interrupt called on instance {id(self)}")
        self._interrupted = True

        if self._chat_model and hasattr(self._chat_model, "set_interrupted"):
            self.logger.info(
                f"Setting interrupt on chat_model {id(self._chat_model)}"
            )
            self._chat_model.set_interrupted(True)
        else:
            self.logger.warning(
                f"Chat model not available or missing set_interrupted: {self._chat_model}"
            )

        if self._workflow_manager and hasattr(
            self._workflow_manager, "set_interrupted"
        ):
            self.logger.info(
                f"Setting interrupt on workflow_manager {id(self._workflow_manager)}"
            )
            self._workflow_manager.set_interrupted(True)
        else:
            self.logger.warning(
                f"Workflow manager not available: {self._workflow_manager}"
            )

    def on_section_changed(self) -> None:
        """Handle section change events."""
        self.logger.info("Section changed, clearing history")
        self.clear_history()

    # Specialized model methods
