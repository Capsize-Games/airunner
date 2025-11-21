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
    BatchProcessingMixin,
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
    BatchProcessingMixin,
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
        self.logger.info(
            f"load() called, current status: {self.model_status[ModelType.LLM]}"
        )
        if self.model_status[ModelType.LLM] in (
            ModelStatus.LOADING,
            ModelStatus.LOADED,
        ):
            self.logger.info(
                f"Returning early - model already in state: {self.model_status[ModelType.LLM]}"
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
                f"Cannot load model: {prepare_result.get('reason', 'Unknown reason')}"
            )
            self.change_model_status(ModelType.LLM, ModelStatus.FAILED)
            self.logger.info(
                f"[LLM LOAD] Model cannot be loaded - resource conflict"
            )
            return

        if self.llm_settings.use_local_llm:
            self._send_quantization_info()

        self._load_local_llm_components()

        self._load_chat_model()
        self.logger.info(
            f"[LLM LOAD] Chat model loaded: {self._chat_model is not None}"
        )

        self._load_tool_manager()
        self.logger.info(
            f"[LLM LOAD] Tool manager loaded: {self._tool_manager is not None}"
        )

        self._load_workflow_manager()
        self.logger.info(
            f"[LLM LOAD] Workflow manager loaded: {self._workflow_manager is not None}"
        )

        self._update_model_status()
        self.logger.info(
            f"[LLM LOAD] Model status updated to: {self.model_status[ModelType.LLM]}"
        )

        # Mark model as loaded
        self.logger.info(
            f"[LLM LOAD] Marking model as loaded in resource manager"
        )
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

        # Store request_id for use in response correlation
        self._current_request_id = data.get("request_id")

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

        # Check if use_memory=False - if so, clear conversation history
        llm_request = data["request_data"].get("llm_request")
        self.llm_request = llm_request
        if llm_request and not llm_request.use_memory:
            self.logger.info(
                "use_memory=False - clearing conversation history for this request"
            )
            if self._workflow_manager:
                self._workflow_manager.clear_memory()

        conversation = self._get_or_create_conversation(data)
        if conversation and self._workflow_manager:
            self._workflow_manager.set_conversation_id(
                conversation.id,
                ephemeral=llm_request.ephemeral_conversation,
            )

        # Check if tool_categories specified - if so, filter tools
        tools_filtered = False
        system_prompt = None  # Extract system prompt from request
        if llm_request:
            self.logger.info(
                f"[LLM MANAGER DEBUG] llm_request.tool_categories={llm_request.tool_categories}"
            )
            # Extract system_prompt if provided
            if (
                hasattr(llm_request, "system_prompt")
                and llm_request.system_prompt
            ):
                system_prompt = llm_request.system_prompt
                self.logger.info(
                    f"Using custom system prompt from request: {system_prompt[:100]}..."
                )

        # Handle Auto mode: intelligently select tool categories based on prompt
        if llm_request and llm_request.tool_categories is None:
            self.logger.info(
                "Auto mode: Analyzing prompt to select relevant tool categories"
            )
            selected_categories = self._classify_prompt_for_tools(
                data["request_data"]["prompt"]
            )
            self.logger.info(
                f"Auto mode selected categories: {selected_categories}"
            )
            self._apply_tool_filter(selected_categories)
            tools_filtered = True
        elif llm_request and llm_request.tool_categories is not None:
            self.logger.info(
                f"[LLM MANAGER DEBUG] APPLYING TOOL FILTER with {llm_request.tool_categories}"
            )
            self.logger.info(
                f"Applying tool filter with categories: {llm_request.tool_categories}"
            )
            self._apply_tool_filter(llm_request.tool_categories)
            tools_filtered = True
        else:
            self.logger.info(
                f"[LLM MANAGER DEBUG] NOT APPLYING FILTER - tool_categories is None"
            )
            self.logger.info("No tool filtering - using all tools")

        # If rag_files were provided, ensure they are loaded into the RAG
        # engine and indexed before generation. This avoids a race where the
        # worker loads files but indexing is not ready when the LLM runs.
        if llm_request and getattr(llm_request, "rag_files", None):
            try:
                rag_files = llm_request.rag_files
                if hasattr(self, "ensure_indexed_files"):
                    # Prefer the mixin helper which handles file tracking
                    self.ensure_indexed_files(rag_files)
                else:
                    # Fallback: load files individually
                    for doc in rag_files:
                        if isinstance(doc, str):
                            self.load_file_into_rag(doc)
                        elif isinstance(doc, (bytes, bytearray)):
                            self.load_bytes_into_rag(doc, source_name="upload")
                        elif isinstance(doc, dict) and doc.get("content"):
                            ft = doc.get("file_type", "")
                            content = doc.get("content")
                            if ft.lower() in [".epub", ".pdf"]:
                                b = (
                                    content
                                    if isinstance(content, (bytes, bytearray))
                                    else str(content).encode("utf-8")
                                )
                                self.load_bytes_into_rag(
                                    b,
                                    source_name=doc.get(
                                        "source_name", "upload"
                                    ),
                                    file_ext=ft,
                                )
                            elif ft.lower() in [".html", ".htm", ".md"]:
                                self.load_html_into_rag(
                                    str(content),
                                    source_name=doc.get(
                                        "source_name", "web_content"
                                    ),
                                )
                            else:
                                self.load_html_into_rag(
                                    str(content),
                                    source_name=doc.get(
                                        "source_name", "web_content"
                                    ),
                                )
            except Exception as e:
                self.logger.warning(
                    f"Error ensuring rag files are indexed: {e}"
                )

        return self._do_generate(
            prompt=data["request_data"]["prompt"],
            action=data["request_data"]["action"],
            system_prompt=system_prompt,  # Pass extracted system prompt
            llm_request=data["request_data"]["llm_request"],
            extra_context=extra_context,
            skip_tool_setup=tools_filtered,  # Pass flag to prevent tool override
        )

    def _apply_tool_filter(self, tool_categories: List[str]) -> None:
        """Apply tool category filter to workflow manager.

        Args:
            tool_categories: List of allowed category names. Empty list = no tools.
                           None = all tools (handled by caller).
                           Supports aliases like "USER_DATA" -> "SYSTEM", "KNOWLEDGE" -> "RAG"
        """
        self.logger.info(
            f"[TOOL FILTER] ENTER _apply_tool_filter with categories: {tool_categories}"
        )
        if not self._workflow_manager or not self._tool_manager:
            self.logger.warning(
                "Cannot apply tool filter - workflow_manager or tool_manager not initialized"
            )
            self.logger.info(
                f"[TOOL FILTER] workflow_manager: {self._workflow_manager}, tool_manager: {self._tool_manager}"
            )
            return

        if tool_categories is not None and len(tool_categories) == 0:
            # Empty list means: disable ALL tools for this request
            self.logger.info(
                "tool_categories=[] - disabling all tools for this request"
            )
            self._workflow_manager.update_tools([])
            self._workflow_manager._build_and_compile_workflow()
            self.logger.info(
                "Tools disabled successfully - workflow rebuilt with 0 tools"
            )
            return

        if tool_categories is None:
            # None means: enable ALL tools for this request
            self.logger.info(
                "tool_categories=None - enabling all tools for this request"
            )
            all_tools = self._tool_manager.get_all_tools()
            self._workflow_manager.update_tools(all_tools)
            self._workflow_manager._build_and_compile_workflow()
            self.logger.info(
                f"All tools enabled successfully - workflow rebuilt with {len(all_tools)} tools"
            )
            return

        # Filter tools by category
        from airunner.components.llm.core.tool_registry import ToolCategory

        # Category alias mapping for common names
        CATEGORY_ALIASES = {
            "user_data": "system",  # USER_DATA -> SYSTEM (user data tools in SYSTEM)
            "knowledge": "rag",  # KNOWLEDGE -> RAG (knowledge tools in RAG)
            "agent": "system",  # AGENT -> SYSTEM (agent tools in SYSTEM)
            "agents": "system",  # AGENTS -> SYSTEM
        }

        allowed_categories = set()
        for cat_name in tool_categories:
            cat_lower = cat_name.lower()

            # Check if this is an alias
            if cat_lower in CATEGORY_ALIASES:
                actual_cat = CATEGORY_ALIASES[cat_lower]
                self.logger.info(
                    f"Mapped alias '{cat_name}' to category '{actual_cat}'"
                )
                cat_lower = actual_cat

            try:
                # Convert string to ToolCategory enum
                category = ToolCategory(cat_lower)
                allowed_categories.add(category)
                self.logger.info(f"Added category: {category.value}")
            except ValueError:
                self.logger.warning(
                    f"Unknown tool category: {cat_name}. "
                    f"Valid categories: {[c.value for c in ToolCategory]}. "
                    f"Valid aliases: {list(CATEGORY_ALIASES.keys())}"
                )
        # Debug: Log the allowed categories for visibility in server logs
        debug_allowed = [c.value for c in allowed_categories]
        self.logger.info(
            f"[TOOL FILTER DEBUG] allowed_categories computed: {debug_allowed}"
        )
        if not allowed_categories:
            self.logger.warning(
                "No valid tool categories specified - using all tools"
            )
            return

        self.logger.info(
            f"[TOOL FILTER] Getting tools by categories: {list(allowed_categories)}",
        )
        filtered_tools = self._tool_manager.get_tools_by_categories(
            list(allowed_categories)
        )
        # Debug: Log the filtered tools (names) for verification
        try:
            filtered_names = [
                getattr(t, "name", getattr(t, "__name__", str(t)))
                for t in filtered_tools
            ]
        except Exception:
            filtered_names = str(filtered_tools)
        self.logger.info(
            f"[TOOL FILTER DEBUG] Filtered tools: {filtered_names}"
        )
        self.logger.info(
            f"[TOOL FILTER] Got {len(filtered_tools)} filtered tools",
        )
        self.logger.info(
            f"Filtered to {len(filtered_tools)} tools from categories: {tool_categories}"
        )
        self.logger.info(
            f"[TOOL FILTER] Calling update_tools with {len(filtered_tools)} tools",
        )
        self._workflow_manager.update_tools(filtered_tools)

    def _classify_prompt_for_tools(self, prompt: str) -> list:
        """
        Analyze a prompt and intelligently select which tool categories are needed.

        Uses keyword matching and pattern detection to quickly classify intent
        without making an LLM call. This keeps Auto mode fast.

        Args:
            prompt: User's input text

        Returns:
            List of tool category strings (empty list if no tools needed)
        """
        prompt_lower = prompt.lower()
        selected_categories = []

        # Web/scraping keywords → Maps to "search" category
        if any(
            word in prompt_lower
            for word in [
                "scrape",
                "fetch",
                "download",
                "crawl",
                "extract from",
                "get content",
                "webpage",
                "website",
                "url",
                "http",
            ]
        ):
            selected_categories.append(
                "search"
            )  # Web scraping tools are in SEARCH category        # Math/calculation keywords - be more specific to avoid false positives
        has_math_word = any(
            word in prompt_lower
            for word in [
                "calculate",
                "compute",
                "solve",
                " what is ",  # Space-bounded to avoid matching "what issue"
                "how much",
                "equation",
                " math",
                "addition",
                "subtract",
                "multiply",
                "divide",
                " sum ",  # Space-bounded to avoid matching "sum" in "summarize"
                "total",
            ]
        )
        # Only check for operators if there's no URL in the prompt
        has_url = "http" in prompt_lower or "www." in prompt_lower
        has_math_operator = not has_url and (
            any(op in prompt_lower for op in ["+", "*", "/", "="])
            or "-" in prompt_lower
        )

        if has_math_word or has_math_operator:
            selected_categories.append("math")

        # File operations keywords
        if any(
            word in prompt_lower
            for word in [
                "read file",
                "write file",
                "save to",
                "open file",
                "create file",
                "delete file",
                "list files",
                "directory",
            ]
        ):
            selected_categories.append("file")

        # Time/date keywords
        if any(
            word in prompt_lower
            for word in [
                "time",
                "date",
                "today",
                "tomorrow",
                "yesterday",
                "schedule",
                "calendar",
                "when is",
                "what day",
            ]
        ):
            selected_categories.append("time")

        # Search/research keywords
        if any(
            word in prompt_lower
            for word in [
                "search",
                "find",
                "look up",
                "research",
                "information about",
                "tell me about",
                "what do you know",
                "explain",
            ]
        ):
            selected_categories.append("search")

        # Conversation management keywords
        if any(
            word in prompt_lower
            for word in [
                "clear history",
                "clear conversation",
                "new conversation",
                "switch conversation",
                "list conversations",
                "delete conversation",
                "conversation history",
            ]
        ):
            selected_categories.append("conversation")

        # If no specific tools detected, return empty list (no tools needed)
        # This makes simple chat like "hello" fast
        if not selected_categories:
            self.logger.info(
                f"Auto mode: No tools needed for prompt: '{prompt[:50]}...'"
            )
            return []

        self.logger.info(
            f"Auto mode: Selected {len(selected_categories)} categories: {selected_categories}"
        )
        return selected_categories

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
