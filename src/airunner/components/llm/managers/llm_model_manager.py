from typing import Any, Optional

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

                    # Fallback: try whitespace-separated tokens if comma parsing failed
                    if not selected_categories:
                        for token in candidate_text.replace(",", " ").split():
                            token_clean = token.strip().strip(".;:")
                            if token_clean in available_categories and token_clean not in selected_categories:
                                selected_categories.append(token_clean)
                    
                    # Limit to a small set to avoid binding every tool
                    if len(selected_categories) > 5:
                        selected_categories = selected_categories[:5]
                    
                    # Always include search for questions that might need current info
                    # The LLM should have included it, but ensure it's there for safety
                    if not selected_categories:
                        self.logger.info("Auto mode: No valid categories parsed, defaulting to search")
                        selected_categories = ["search"]
                    
                    self.logger.info(
                        f"Auto mode (LLM): Selected {len(selected_categories)} categories: {selected_categories}"
                    )
                    return selected_categories
        except Exception as e:
            self.logger.warning(f"LLM classification failed: {e}, falling back to all tools")
        
        # Fallback: provide all common categories if LLM classification fails
        self.logger.info("Auto mode: Classification unavailable, providing broad tool access")
        return ["search", "knowledge", "system", "math"]

    def _should_use_harness(self, prompt: str) -> bool:
        """Check if a prompt should use the long-running harness.

        The harness is used for:
        - Multi-step tasks (e.g., "implement these 5 features")
        - Complex coding projects (e.g., "refactor and add tests")
        - Multi-topic research (e.g., "research 5 papers on X")

        Args:
            prompt: User's input text

        Returns:
            True if the harness should be used
        """
        try:
            from airunner.components.llm.long_running import should_use_harness

            use_harness, analysis = should_use_harness(prompt)
            if use_harness and analysis:
                self.logger.info(
                    f"Harness recommended: {analysis.task_type.value} "
                    f"(confidence: {analysis.confidence:.2f}) - {analysis.reason}"
                )
            return use_harness
        except ImportError:
            self.logger.debug("Long-running harness not available")
            return False
        except Exception as e:
            self.logger.warning(f"Error checking harness applicability: {e}")
            return False

    def _restore_all_tools(self) -> None:
        """Restore all tools to workflow manager (called after filtered request)."""
        if self._workflow_manager and self._tool_manager:
            all_tools = self._tool_manager.get_all_tools()
            self._workflow_manager.update_tools(all_tools)

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
