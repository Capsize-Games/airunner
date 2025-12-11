from datetime import datetime
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
    LLMActionType,
    ModelType,
    ModelStatus,
    SignalCode,
)
from airunner.utils.memory import clear_memory
from airunner.components.llm.managers.llm_settings import LLMSettings
from airunner.components.documents.data.models.document import (
    Document,
)
from airunner.components.data.session_manager import (
    session_scope,
)


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
        if not self._current_request_id:
            self.logger.warning("[REQUEST] Missing request_id on incoming request; streaming responses will not be routed")
        else:
            self.logger.debug(f"[REQUEST] Set _current_request_id={self._current_request_id}")

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

        # Check if mode routing parameters changed - if so, reload workflow manager
        if llm_request and (
            getattr(llm_request, "use_mode_routing", False)
            or getattr(llm_request, "mode_override", None)
        ):
            use_mode_routing = getattr(llm_request, "use_mode_routing", False)
            mode_override = getattr(llm_request, "mode_override", None)

            # Check if workflow manager needs to be rebuilt with new mode settings
            needs_rebuild = False
            if self._workflow_manager:
                current_mode_routing = getattr(
                    self._workflow_manager, "_use_mode_routing", False
                )
                current_mode_override = getattr(
                    self._workflow_manager, "_mode_override", None
                )
                if (
                    current_mode_routing != use_mode_routing
                    or current_mode_override != mode_override
                ):
                    needs_rebuild = True
                    self.logger.info(
                        f"Mode routing settings changed: "
                        f"use_mode_routing={use_mode_routing}, "
                        f"mode_override={mode_override} - "
                        f"rebuilding workflow manager"
                    )
            else:
                needs_rebuild = True

            if needs_rebuild:
                # Unload and reload workflow manager with new settings
                self._unload_workflow_manager()
                self._load_workflow_manager()

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
            # Emit status signal for UI feedback during classification
            self.emit_signal(
                SignalCode.LLM_TOOL_STATUS_SIGNAL,
                {
                    "tool_id": "tool_classification",
                    "tool_name": "tool_analyzer",
                    "query": data["request_data"]["prompt"][:100],
                    "status": "starting",
                    "details": "Analyzing prompt to select tools...",
                    "conversation_id": getattr(self, "_conversation_id", None),
                    "timestamp": datetime.utcnow().isoformat(),
                },
            )
            selected_categories = self._classify_prompt_for_tools(
                data["request_data"]["prompt"]
            )
            # Emit completion status
            self.emit_signal(
                SignalCode.LLM_TOOL_STATUS_SIGNAL,
                {
                    "tool_id": "tool_classification",
                    "tool_name": "tool_analyzer",
                    "query": data["request_data"]["prompt"][:100],
                    "status": "completed",
                    "details": f"Selected: {', '.join(selected_categories) if selected_categories else 'none'}",
                    "conversation_id": getattr(self, "_conversation_id", None),
                    "timestamp": datetime.utcnow().isoformat(),
                },
            )
            self.logger.info(
                f"Auto mode selected categories: {selected_categories}"
            )
            action = data["request_data"].get("action")
            force_tool = getattr(llm_request, "force_tool", None) if llm_request else None
            self._apply_tool_filter(
                selected_categories,
                action=action,
                force_tool=force_tool,
            )
            tools_filtered = True
        elif llm_request and llm_request.tool_categories is not None:
            self.logger.info(
                f"[LLM MANAGER DEBUG] APPLYING TOOL FILTER with {llm_request.tool_categories}"
            )
            self.logger.info(
                f"Applying tool filter with categories: {llm_request.tool_categories}"
            )
            action = data["request_data"].get("action")
            force_tool = getattr(llm_request, "force_tool", None)
            self._apply_tool_filter(llm_request.tool_categories, action=action, force_tool=force_tool)
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

        # If the request has no explicit rag_files but search tools were
        # selected, auto-attach active, indexed docs from the DB so that
        # the model can use local knowledge (RAG) when appropriate.
        try:
            if llm_request and not getattr(llm_request, "rag_files", None):
                # Only do this auto-load when 'search' is in selected categories
                # and we have rag indexing available in the manager
                if "search" in (selected_categories or []) and hasattr(
                    self, "ensure_indexed_files"
                ):
                    with session_scope() as session:
                        docs = (
                            session.query(Document)
                            .filter_by(active=True, indexed=True)
                            .all()
                        )

                        if docs:
                            # Select a small number (3) of candidate docs to load
                            cand = [d.path for d in docs[:3]]
                            llm_request.rag_files = cand
                            self.logger.info(
                                f"Auto-attached {len(cand)} indexed document(s) to rag_files for search: {cand}"
                            )
                            # Ensure they are indexed/loaded now
                            self.ensure_indexed_files(cand)
        except Exception:
            # Best-effort auto-load; if it fails, just continue without RAG
            self.logger.debug(
                "Auto attachment of RAG files failed, continuing without local RAG."
            )

        return self._do_generate(
            prompt=data["request_data"]["prompt"],
            action=data["request_data"]["action"],
            system_prompt=system_prompt,  # Pass extracted system prompt
            llm_request=data["request_data"]["llm_request"],
            extra_context=extra_context,
            skip_tool_setup=tools_filtered,  # Pass flag to prevent tool override
        )

    # Categories that are ALWAYS included regardless of filtering
    # Only knowledge tools are always included - these are safe internal tools
    # for storing/retrieving user facts and conversation memory.
    # Search tools (web search) are NOT included by default to prevent
    # unwanted internet searches when the caller only wants local tools like RAG.
    ALWAYS_INCLUDE_CATEGORIES = {"knowledge"}

    def _apply_tool_filter(
        self, tool_categories: List[str], action=None, force_tool: Optional[str] = None
    ) -> None:
        """Apply tool category filter to workflow manager.

        Args:
            tool_categories: List of allowed category names. Empty list = no tools.
                           None = all tools (handled by caller).
                           Supports aliases like "USER_DATA" -> "SYSTEM", "KNOWLEDGE" -> "RAG"
            action: The LLMActionType for this request
            force_tool: Optional tool name to force the LLM to call first
                           
        Note:
            Categories in ALWAYS_INCLUDE_CATEGORIES are always added regardless
            of the filter. This ensures knowledge/memory tools are always available.
            
            When force_tool is set, tool_choice will be configured to REQUIRE
            that specific tool to be called first.
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

        # Import here to avoid circular imports
        from airunner.components.llm.core.tool_registry import ToolCategory

        if tool_categories is not None and len(tool_categories) == 0:
            # Empty list means: only include ALWAYS_INCLUDE_CATEGORIES
            self.logger.info(
                "tool_categories=[] - including only always-available tools (knowledge)"
            )
            always_tools = self._tool_manager.get_tools_by_categories(
                [ToolCategory(cat) for cat in self.ALWAYS_INCLUDE_CATEGORIES],
                include_deferred=False,  # Only immediate tools
            )
            self._workflow_manager.update_tools(always_tools)
            self._workflow_manager._build_and_compile_workflow()
            self.logger.info(
                f"Always-available tools enabled - workflow rebuilt with {len(always_tools)} tools"
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
            "user_data": "knowledge",  # USER_DATA -> KNOWLEDGE (user data tools moved to KNOWLEDGE)
            "agent": "system",  # AGENT -> SYSTEM (agent tools in SYSTEM)
            "agents": "system",  # AGENTS -> SYSTEM
            "memory": "knowledge",  # MEMORY -> KNOWLEDGE (memory tools in KNOWLEDGE)
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

        # Always add ALWAYS_INCLUDE_CATEGORIES to the allowed categories
        for always_cat in self.ALWAYS_INCLUDE_CATEGORIES:
            try:
                category = ToolCategory(always_cat)
                if category not in allowed_categories:
                    allowed_categories.add(category)
                    self.logger.info(f"Added always-include category: {category.value}")
            except ValueError:
                pass

        self.logger.info(
            f"[TOOL FILTER] Getting tools by categories: {list(allowed_categories)}",
        )
        # When filtering by category, include ALL tools in those categories
        # (including deferred ones). The defer_loading flag is only meant to
        # reduce the global tool count when no category filter is applied.
        # If the LLM classified that it needs certain categories, it should
        # have access to all tools in those categories.
        filtered_tools = self._tool_manager.get_tools_by_categories(
            list(allowed_categories),
            include_deferred=True,  # Include all tools in selected categories
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
        # Determine tool_choice based on action and force_tool
        tool_choice = None
        if force_tool:
            # Force a specific tool to be called first
            # This uses LangChain's tool_choice format to require a specific function
            tool_choice = {"type": "function", "function": {"name": force_tool}}
            self.logger.info(f"[TOOL FILTER] Forcing tool: {force_tool}")
        elif action == LLMActionType.PERFORM_RAG_SEARCH:
            # For RAG mode, force at least one tool usage
            tool_choice = "any"
        elif action == LLMActionType.CODE:
            # For CODE mode, require tool usage (start_workflow should be called)
            tool_choice = "any"
        elif tool_categories and ("search" in tool_categories or "research" in tool_categories):
            # Search intent: require at least one tool call to avoid hallucinated answers
            tool_choice = "any"
            
        self._workflow_manager.update_tools(
            filtered_tools, tool_choice=tool_choice
        )

    def _classify_prompt_for_tools(self, prompt: str) -> list:
        """
        Analyze a prompt using the LLM to intelligently select which tool categories are needed.

        Uses the LLM itself to understand user intent and select appropriate tool categories.
        This provides much better accuracy than keyword matching.

        Args:
            prompt: User's input text

        Returns:
            List of tool category strings (empty list if no tools needed)
        """
        # Fast-path: trivial greetings/short chit-chat should not trigger tools
        prompt_lc = (prompt or "").strip().lower()
        if len(prompt_lc) <= 40:
            greeting_tokens = [
                "hello",
                "hi",
                "hey",
                "hola",
                "yo",
                "sup",
                "morning",
                "afternoon",
                "evening",
                "thanks",
                "thank you",
            ]
            if any(token in prompt_lc for token in greeting_tokens):
                self.logger.info("Auto mode: greeting detected, disabling tools")
                return []

        # Fast-path: obvious web search intent should always enable search tools
        search_triggers = [
            "search",
            "look up",
            "lookup",
            "find",
            "google",
            "bing",
            "duckduckgo",
            "ddg",
            "web",
            "internet",
            "news",
            "latest",
            "recent",
        ]
        if any(trigger in prompt_lc for trigger in search_triggers):
            self.logger.info("Auto mode: search intent detected, forcing search category")
            return ["search"]

        # Get available categories from ToolCategory enum
        from airunner.components.llm.core.tool_registry import ToolCategory
        
        available_categories = [cat.value for cat in ToolCategory]
        
        # Concise classification prompt - faster than verbose version
        # Add /no_think instruction for Qwen3 models to disable thinking mode
        classification_prompt = f"""/no_think
Classify which tool categories are needed for this user message.

Categories: {', '.join(available_categories)}

Message: "{prompt[:500]}"

Reply with ONLY category names (comma-separated) or "none":"""

        try:
            # Use the workflow manager's chat model for classification
            if self._workflow_manager and hasattr(self._workflow_manager, '_original_chat_model'):
                chat_model = self._workflow_manager._original_chat_model
                if chat_model:
                    from langchain_core.messages import HumanMessage
                    
                    # Temporarily disable thinking for fast classification
                    original_thinking = getattr(chat_model, 'enable_thinking', True)
                    if hasattr(chat_model, 'enable_thinking'):
                        chat_model.enable_thinking = False
                    
                    # Use lower temperature for more deterministic classification
                    original_temp = getattr(chat_model, 'temperature', 0.7)
                    if hasattr(chat_model, 'temperature'):
                        chat_model.temperature = 0.1
                    
                    # Temporarily disable tools for classification
                    # This prevents 100+ tool definitions from bloating the context
                    original_tool_choice = getattr(chat_model, 'tool_choice', None)
                    if hasattr(chat_model, 'tool_choice'):
                        chat_model.tool_choice = "none"
                    
                    try:
                        response = chat_model.invoke([HumanMessage(content=classification_prompt)])
                    finally:
                        # Restore original settings
                        if hasattr(chat_model, 'enable_thinking'):
                            chat_model.enable_thinking = original_thinking
                        if hasattr(chat_model, 'temperature'):
                            chat_model.temperature = original_temp
                        if hasattr(chat_model, 'tool_choice'):
                            chat_model.tool_choice = original_tool_choice
                    
                    response_text = response.content if hasattr(response, 'content') else str(response)
                    
                    # Strip any thinking tags that might have leaked through
                    # Supports both Qwen3 <think>...</think> and Ministral 3 [THINK]...[/THINK]
                    if '<think>' in response_text:
                        # Extract content after </think> if present
                        if '</think>' in response_text:
                            response_text = response_text.split('</think>')[-1]
                        else:
                            # No closing tag - try to get first line after think
                            response_text = response_text.split('<think>')[0]
                    elif '[THINK]' in response_text.upper():
                        # Handle Ministral 3 Reasoning [THINK]...[/THINK] tags
                        import re
                        response_text = re.sub(r'\[THINK\].*?\[/THINK\]', '', response_text, flags=re.DOTALL | re.IGNORECASE)
                        # Remove any orphaned tags
                        response_text = re.sub(r'\[/?THINK\]', '', response_text, flags=re.IGNORECASE)
                    
                    # Parse the response
                    import re
                    response_text = response_text.strip().lower()
                    # Drop echoed category listings so we don't select every tool
                    response_text = re.sub(
                        r"categories:\s*[a-z,\s]+", "", response_text, flags=re.IGNORECASE
                    )
                    cleaned_lines = [line.strip() for line in response_text.splitlines() if line.strip()]
                    candidate_text = cleaned_lines[0] if cleaned_lines else response_text
                    self.logger.info(f"LLM classification response: {candidate_text}")
                    
                    if candidate_text == "none" or not candidate_text:
                        self.logger.info("Auto mode: LLM determined no tools needed")
                        return []
                    
                    # Parse comma-separated categories from the first non-empty line
                    selected_categories = []
                    for cat in candidate_text.split(","):
                        token = cat.strip()
                        if token in available_categories and token not in selected_categories:
                            selected_categories.append(token)

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
