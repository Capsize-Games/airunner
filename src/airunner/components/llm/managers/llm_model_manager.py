import gc
import random
import os
import json
import torch
from typing import Optional, Dict, Any, List, Union

from peft import PeftModel
from transformers.utils.quantization_config import (
    BitsAndBytesConfig,
    GPTQConfig,
)
from transformers import AutoModelForCausalLM, AutoTokenizer
from transformers.generation.streamers import TextIteratorStreamer
from langchain_core.messages import AIMessage

from airunner.components.conversations.conversation_history_manager import (
    ConversationHistoryManager,
)
from airunner.components.llm.data.conversation import Conversation
from airunner.components.llm.data.fine_tuned_model import FineTunedModel
from airunner.components.application.managers.base_model_manager import (
    BaseModelManager,
)
from airunner.components.llm.adapters import ChatModelFactory
from airunner.components.llm.managers.tool_manager import ToolManager
from airunner.components.llm.managers.workflow_manager import WorkflowManager
from airunner.enums import (
    ModelType,
    ModelStatus,
    LLMActionType,
    SignalCode,
)
from airunner.settings import (
    AIRUNNER_MAX_SEED,
    AIRUNNER_LOCAL_FILES_ONLY,
)
from airunner.utils.memory import clear_memory
from airunner.utils.settings.get_qsettings import get_qsettings
from airunner.components.llm.managers.training_mixin import TrainingMixin
from airunner.components.llm.managers.llm_request import LLMRequest
from airunner.components.llm.managers.llm_response import LLMResponse
from airunner.components.llm.managers.llm_settings import LLMSettings


class LLMModelManager(BaseModelManager, TrainingMixin):
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

    # Model components
    _model: Optional[AutoModelForCausalLM] = None
    _streamer: Optional[TextIteratorStreamer] = None
    _tokenizer: Optional[object] = None
    _current_model_path: Optional[str] = None

    # LangChain/LangGraph components
    _chat_model: Optional[Any] = None
    _tool_manager: Optional[ToolManager] = None
    _workflow_manager: Optional[WorkflowManager] = None

    # Other components
    _history: Optional[List] = []

    # Settings
    llm_settings: LLMSettings

    def __init__(
        self,
        *args,
        **kwargs,
    ):
        """
        Initialize the LLM handler.

        Args:
            *args: Variable length argument list passed to parent classes.
            **kwargs: Arbitrary keyword arguments passed to parent classes.
        """
        super().__init__(*args, **kwargs)
        # Initialize the instance status *after* the base class init
        self._model_status = {ModelType.LLM: ModelStatus.UNLOADED}
        self.llm_settings = LLMSettings()
        self._pending_conversation_message = None
        self._conversation_history_manager = ConversationHistoryManager()

    @property
    def system_prompt(self) -> str:
        """Generate the system prompt for the LLM."""
        from datetime import datetime

        parts = []

        if hasattr(self, "chatbot") and self.chatbot:
            parts.append(
                f"You are {self.chatbot.bot_name}, a helpful AI assistant."
            )

            if (
                hasattr(self.chatbot, "personality")
                and self.chatbot.personality
            ):
                parts.append(f"Personality: {self.chatbot.personality}")
        else:
            parts.append("You are a helpful AI assistant.")

        # Add date/time context
        now = datetime.now()
        parts.append(
            f"Current date and time: {now.strftime('%Y-%m-%d %H:%M:%S')}"
        )

        # Add mood update instructions if enabled
        if (
            self.llm_settings.use_chatbot_mood
            and hasattr(self, "chatbot")
            and self.chatbot
            and hasattr(self.chatbot, "use_mood")
            and self.chatbot.use_mood
        ):
            parts.append(
                f"\nYou have access to an update_mood tool. "
                f"Every {self.llm_settings.update_mood_after_n_turns} conversation turns, "
                f"reflect on the conversation and update your emotional state by calling the "
                f"update_mood tool with a one-word emotion (e.g., happy, sad, excited, thoughtful, "
                f"confused) and a matching emoji (e.g., 😊, 😢, 🤔, 😐). "
                f"Your mood should reflect your personality and the context of the conversation."
            )

        return "\n\n".join(parts)

    def get_system_prompt_for_action(self, action: LLMActionType) -> str:
        """Generate a system prompt tailored to the specific action type.

        Args:
            action: The type of action being performed

        Returns:
            System prompt with action-specific instructions
        """
        base_prompt = self.system_prompt

        # Add action-specific tool usage instructions
        if action == LLMActionType.CHAT:
            base_prompt += (
                "\n\nMode: CHAT"
                "\nFocus on natural conversation. You may use conversation management tools "
                "(clear_conversation, toggle_tts) and data storage tools as needed, but avoid "
                "image generation or RAG search unless explicitly requested by the user."
            )

        elif action == LLMActionType.GENERATE_IMAGE:
            base_prompt += (
                "\n\nMode: IMAGE GENERATION"
                "\nYour primary focus is generating images. Use the generate_image tool "
                "to create images based on user descriptions. You may also use canvas tools "
                "(clear_canvas, open_image) to manage the workspace."
            )

        elif action == LLMActionType.PERFORM_RAG_SEARCH:
            base_prompt += (
                "\n\nMode: DOCUMENT SEARCH"
                "\nYour primary focus is searching through uploaded documents. Use the rag_search "
                "tool to find relevant information in the document database. You may also use "
                "search_web for supplementary internet searches."
            )

        elif action == LLMActionType.APPLICATION_COMMAND:
            base_prompt += (
                "\n\nMode: AUTO (Full Capabilities)"
                "\nYou have access to all tools and should autonomously determine which tools "
                "to use based on the user's request. Analyze the intent and choose the most "
                "appropriate tools to fulfill the user's needs."
            )

        return base_prompt

    @property
    def tools(self) -> List:
        """Get all available tools from tool manager."""
        if self._tool_manager:
            return self._tool_manager.get_all_tools()
        return []

    @property
    def is_mistral(self) -> bool:
        """
        Check if the current model is a Mistral model.

        Returns:
            bool: True if the model is a Mistral model, False otherwise.
        """
        if not self._current_model_path:
            return False
        path = self._current_model_path.lower()
        return "mistral" in path

    @property
    def is_llama_instruct(self) -> bool:
        """
        Check if the current model is a LLaMA instruct model.

        Returns:
            bool: True if the model is a LLaMA instruct model, False otherwise.
        """
        if not self._current_model_path:
            return False
        path = self._current_model_path.lower()
        return "instruct" in path and "llama" in path

    @property
    def _quantization_config(
        self,
    ) -> Optional[Union[BitsAndBytesConfig, GPTQConfig]]:
        """
        Get the appropriate quantization configuration based on dtype settings.

        Returns:
            Optional[Union[BitsAndBytesConfig, GPTQConfig]]: Configuration for model quantization,
            or None if no quantization is specified.
        """
        config = None
        if self.llm_dtype == "8bit":
            config = BitsAndBytesConfig(
                llm_int8_threshold=6.0,
                llm_int8_has_fp16_weight=False,
                bnb_4bit_compute_dtype=torch.bfloat16,
                bnb_4bit_use_double_quant=True,
                bnb_4bit_quant_type="nf4",
            )
        elif self.llm_dtype == "4bit":
            config = BitsAndBytesConfig(
                load_in_4bit=True, bnb_4bit_compute_dtype=torch.float16
            )
        elif self.llm_dtype == "2bit":
            config = GPTQConfig(
                bits=2, dataset="c4", tokenizer=self._tokenizer
            )
        return config

    @property
    def use_cache(self) -> bool:
        """
        Determine whether to use model caching based on settings.

        Returns:
            bool: True if cache should be used, False otherwise.
        """
        if self.llm_generator_settings.override_parameters:
            return self.llm_generator_settings.use_cache
        return self.chatbot.use_cache

    @property
    def model_version(self) -> str:
        """
        Get the model version to use based on settings.

        Returns:
            str: The model version identifier.
        """
        model_version = self.chatbot.model_version
        if self.llm_generator_settings.override_parameters:
            model_version = self.llm_generator_settings.model_version
        return model_version

    @property
    def model_name(self) -> str:
        return "causallm/w4ffl35/Ministral-8B-Instruct-2410-doublequant"

    @property
    def model_path(self) -> str:
        """
        Get the filesystem path to the model files.

        Returns:
            str: Absolute path to the model directory.
        """
        return os.path.expanduser(
            os.path.join(
                self.path_settings.base_path,
                "text",
                "models",
                "llm",
                self.model_name,
            )
        )

    def load(self) -> None:
        """
        Load the LLM model and associated components.

        This method handles the complete loading process, including:
        - Checking if the model is already loaded
        - Loading the tokenizer and model (for local LLM)
        - Creating the appropriate ChatModel via factory
        - Loading the tool manager
        - Loading the workflow manager
        - Updating the model status based on loading results
        """
        # Skip if already loading or loaded
        if self.model_status[ModelType.LLM] in (
            ModelStatus.LOADING,
            ModelStatus.LOADED,
        ):
            return

        # Set status to LOADING before calling unload to avoid recursion/hang
        self.change_model_status(ModelType.LLM, ModelStatus.LOADING)
        self.unload()
        self._current_model_path = self.model_path

        # Load components based on settings
        if self.llm_settings.use_local_llm:
            # Local HuggingFace: load model and tokenizer first
            self._load_tokenizer()
            self._load_model()

        # Create ChatModel (works for all backends)
        self._load_chat_model()

        # Load tools and workflow
        self._load_tool_manager()
        self._load_workflow_manager()

        # Update status
        self._update_model_status()

    def _update_model_status(self):
        """Update model status based on what's loaded."""
        # For API-based models, we don't need model/tokenizer
        is_api = self.llm_settings.use_api

        # Check what we need
        needs_model_and_tokenizer = self.llm_settings.use_local_llm

        # Determine if successfully loaded
        if is_api:
            # API mode: just need chat_model and workflow_manager
            if self._chat_model and self._workflow_manager:
                self.change_model_status(ModelType.LLM, ModelStatus.LOADED)
                self.emit_signal(
                    SignalCode.TOGGLE_LLM_SIGNAL, {"enabled": True}
                )
                return
        else:
            # Local mode: need model, tokenizer, chat_model, and workflow_manager
            if (
                self._model
                and self._tokenizer
                and self._chat_model
                and self._workflow_manager
            ):
                self.change_model_status(ModelType.LLM, ModelStatus.LOADED)
                self.emit_signal(
                    SignalCode.TOGGLE_LLM_SIGNAL, {"enabled": True}
                )

                # Process pending conversation if any
                if getattr(self, "_pending_conversation_message", None):
                    self.logger.info(
                        "Processing pending conversation load after workflow manager became available."
                    )
                    self.load_conversation(self._pending_conversation_message)
                    self._pending_conversation_message = None
                return

        # If we got here, something failed
        if not self._chat_model:
            self.logger.error("ChatModel failed to load")
        if not self._workflow_manager:
            self.logger.error("Workflow manager failed to load")
        if needs_model_and_tokenizer:
            if not self._model:
                self.logger.error("Model failed to load")
            if not self._tokenizer:
                self.logger.error("Tokenizer failed to load")

        self.change_model_status(ModelType.LLM, ModelStatus.FAILED)

    def unload(self) -> None:
        """Unload all LLM components and clear GPU memory."""
        if self.model_status[ModelType.LLM] in (
            ModelStatus.LOADING,
            ModelStatus.UNLOADED,
        ):
            return

        self.change_model_status(ModelType.LLM, ModelStatus.LOADING)
        self._unload_components()
        clear_memory(self.device)
        self.change_model_status(ModelType.LLM, ModelStatus.UNLOADED)

    def _unload_components(self) -> None:
        """Unload all components in sequence."""
        for unload_func in [
            self._unload_workflow_manager,
            self._unload_tool_manager,
            self._unload_chat_model,
            self._unload_tokenizer,
            self._unload_model,
        ]:
            try:
                unload_func()
            except Exception as e:
                self.logger.error(f"Error during unload: {e}", exc_info=True)

    def handle_request(
        self,
        data: Dict,
        extra_context: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Handle an incoming request for LLM generation.

        Args:
            data: Dictionary containing request parameters, including:
                - request_data.prompt: The text prompt to process
                - request_data.action: The type of action to perform
                - request_data.llm_request: Configuration for the request
            extra_context: Dictionary of context keyed by unique identifier (e.g., URL, file path).

        Returns:
            Dict: Dictionary with generation results.
        """
        self.logger.debug("Handling request")
        self._do_set_seed()
        self.load()

        return self._do_generate(
            prompt=data["request_data"]["prompt"],
            action=data["request_data"]["action"],
            llm_request=data["request_data"]["llm_request"],
            extra_context=extra_context,
        )

    def do_interrupt(self) -> None:
        """
        Interrupt the ongoing chat process.

        This can be called to stop a generation that is in progress.
        """
        # For now, interruption is not directly supported in streaming
        # TODO: Implement proper interruption mechanism
        self.logger.warning(
            "Interrupt requested but not yet implemented for workflow manager"
        )

    def on_conversation_deleted(self, data: Dict) -> None:
        """Handle conversation deletion event."""
        # Clear workflow memory if conversation is deleted
        if self._workflow_manager:
            self._workflow_manager.clear_memory()

    def clear_history(self, data: Optional[Dict] = None) -> None:
        """Clear chat history and set up a new conversation."""
        data = data or {}
        conversation = self._get_or_create_conversation(data)

        if conversation:
            Conversation.make_current(conversation.id)

        if self._workflow_manager:
            self._workflow_manager.clear_memory()

    def _get_or_create_conversation(
        self, data: Dict
    ) -> Optional[Conversation]:
        """Get existing conversation or create a new one."""
        conversation_id = data.get("conversation_id")

        if not conversation_id:
            conversation = Conversation.create()
            data["conversation_id"] = conversation.id
            self.update_llm_generator_settings(
                current_conversation_id=conversation.id
            )
            return conversation

        return Conversation.objects.get(conversation_id)

    def add_chatbot_response_to_history(self, message: str) -> None:
        """
        Add a chatbot-generated response to the chat history.

        Args:
            message: The response message to add to history.
        """
        # History is now managed by WorkflowManager's MemorySaver
        # No explicit action needed here
        self.logger.debug(f"Response added to history: {message[:50]}...")

    def load_conversation(self, message: Dict) -> None:
        """
        Load an existing conversation into the chat workflow.

        Args:
            message: Data containing the conversation to load.
                     Expected to have 'conversation_id'.
        """
        conversation_id = message.get("conversation_id")
        self.logger.debug(
            f"Attempting to load conversation ID: {conversation_id}"
        )

        if self._workflow_manager is not None:
            # Update the workflow manager's conversation ID
            if conversation_id and hasattr(
                self._workflow_manager, "set_conversation_id"
            ):
                self._workflow_manager.set_conversation_id(conversation_id)
                self.logger.info(
                    f"Updated workflow manager with conversation ID: {conversation_id}"
                )
            else:
                self.logger.info(
                    f"Workflow manager loaded. Conversation {conversation_id} context available."
                )
            # UI will independently use ConversationHistoryManager to display history
            self._pending_conversation_message = None
        else:
            self.logger.warning(
                f"Workflow manager not loaded. Will use ConversationHistoryManager for conversation ID: {conversation_id}."
            )
            # Store the message so that if the manager loads later, it can sync state
            self._pending_conversation_message = message

    def reload_rag_engine(self) -> None:
        """
        Reload the Retrieval-Augmented Generation engine.

        This is useful when the underlying documents or settings have changed.
        """
        # RAG is now a tool in the tool manager
        # Reload by recreating tool manager
        if self._tool_manager:
            self._unload_tool_manager()
            self._load_tool_manager()
            if self._workflow_manager:
                self._workflow_manager.update_tools(self.tools)
        else:
            self.logger.warning("Cannot reload RAG - tool manager not loaded")

    def on_section_changed(self) -> None:
        """
        Handle section change events.
        """
        # Section tracking is now handled at a higher level
        self.logger.debug("Section changed")

    def _load_tokenizer(self) -> None:
        """
        Load the tokenizer for the selected model.

        Sets self._tokenizer to the loaded tokenizer instance or None if loading fails.
        """
        # Skip if already loaded
        if self._tokenizer is not None:
            return

        self.logger.debug(f"Loading tokenizer from {self.model_path}")
        try:
            self._tokenizer = AutoTokenizer.from_pretrained(
                self.model_path,
                local_files_only=AIRUNNER_LOCAL_FILES_ONLY,
                device_map=self.device,
                trust_remote_code=False,
                torch_dtype=self.torch_dtype,
            )
            self.logger.debug("Tokenizer loaded")

            # Configure tokenizer settings
            if self._tokenizer:
                self._tokenizer.use_default_system_prompt = False
        except Exception as e:
            self.logger.error(f"Error loading tokenizer: {e}")
            self._tokenizer = None
            self.logger.error("Tokenizer failed to load")

    def _load_model(self) -> None:
        """Load the LLM model and apply enabled adapters."""
        if self._model is not None:
            return

        try:
            self._model = AutoModelForCausalLM.from_pretrained(
                self.model_path,
                local_files_only=AIRUNNER_LOCAL_FILES_ONLY,
                use_cache=self.use_cache,
                trust_remote_code=False,
                torch_dtype=self.torch_dtype,
                device_map=self.device,
                attn_implementation=self.attn_implementation,
            )
            self._load_adapters()
        except Exception as e:
            self.logger.error(f"Error loading model: {e}")
            self._model = None

    def _get_enabled_adapter_names(self) -> List[str]:
        """Retrieve enabled adapter names from QSettings."""
        try:
            qs = get_qsettings()
            enabled_adapters_json = qs.value(
                "llm_settings/enabled_adapters", "[]"
            )
            return json.loads(enabled_adapters_json)
        except json.JSONDecodeError as e:
            self.logger.error(f"Error parsing enabled adapters JSON: {e}")
            return []

    def _get_enabled_adapters(
        self, adapter_names: List[str]
    ) -> List[FineTunedModel]:
        """Query database for adapters matching the given names."""
        if not adapter_names:
            return []
        adapters = FineTunedModel.objects.all()
        return [a for a in adapters if a.name in adapter_names]

    def _apply_adapter(self, adapter: FineTunedModel) -> bool:
        """Apply a single adapter to the model."""
        if not adapter.adapter_path or not os.path.exists(
            adapter.adapter_path
        ):
            self.logger.warning(
                f"Adapter '{adapter.name}' path does not exist"
            )
            return False

        try:
            self._model = PeftModel.from_pretrained(
                self._model, adapter.adapter_path
            )
            self._model.eval()
            return True
        except Exception as e:
            self.logger.error(f"Error loading adapter '{adapter.name}': {e}")
            return False

    def _load_adapters(self) -> None:
        """Load all enabled adapters onto the base model."""
        if PeftModel is None:
            return

        try:
            adapter_names = self._get_enabled_adapter_names()
            if not adapter_names:
                return

            enabled_adapters = self._get_enabled_adapters(adapter_names)
            loaded_count = sum(
                self._apply_adapter(a) for a in enabled_adapters
            )

            if loaded_count > 0:
                self.logger.info(f"Loaded {loaded_count} adapter(s)")
        except Exception as e:
            self.logger.error(f"Error loading adapters: {e}")

    def _load_chat_model(self) -> None:
        """
        Create the appropriate LangChain ChatModel based on settings.

        Sets self._chat_model to the created ChatModel instance or None if creation fails.
        """
        if self._chat_model is not None:
            return

        try:
            self.logger.info("Creating ChatModel via factory")

            # Get RAG manager reference if available (for tool manager)
            rag_manager = getattr(self, "rag_manager", None)

            self._chat_model = ChatModelFactory.create_from_settings(
                llm_settings=self.llm_settings,
                model=self._model,
                tokenizer=self._tokenizer,
                chatbot=getattr(self, "chatbot", None),
            )

            self.logger.info(
                f"ChatModel created: {type(self._chat_model).__name__}"
            )
        except Exception as e:
            self.logger.error(f"Error creating ChatModel: {e}", exc_info=True)
            self._chat_model = None

    def _load_tool_manager(self) -> None:
        """Load the tool manager."""
        if self._tool_manager is not None:
            return

        try:
            # Get RAG manager reference if available
            rag_manager = getattr(self, "rag_manager", None)
            self._tool_manager = ToolManager(rag_manager=rag_manager)
            self.logger.info("Tool manager loaded")
        except Exception as e:
            self.logger.error(
                f"Error loading tool manager: {e}", exc_info=True
            )
            self._tool_manager = None

    def _load_workflow_manager(self) -> None:
        """Load the workflow manager."""
        if self._workflow_manager is not None:
            return

        try:
            if not self._chat_model:
                self.logger.error(
                    "Cannot load workflow manager: ChatModel not loaded"
                )
                return

            if not self._tool_manager:
                self.logger.warning(
                    "Tool manager not loaded, workflow will have no tools"
                )

            # Get current conversation ID if available
            conversation_id = None
            try:
                from airunner.settings import SETTINGS

                conversation_id = (
                    SETTINGS.llm_generator_settings.current_conversation_id
                )
            except Exception:
                pass

            self._workflow_manager = WorkflowManager(
                system_prompt=self.system_prompt,
                chat_model=self._chat_model,
                tools=self.tools,
                max_tokens=2000,
                conversation_id=conversation_id,
            )
            self.logger.info(
                f"Workflow manager loaded with conversation ID: {conversation_id}"
            )
        except Exception as e:
            self.logger.error(
                f"Error loading workflow manager: {e}", exc_info=True
            )
            self._workflow_manager = None

    def _unload_chat_model(self) -> None:
        """Unload the chat model from memory."""
        if self._chat_model is not None:
            self.logger.debug("Unloading chat model")
            try:
                del self._chat_model
                self._chat_model = None
            except Exception as e:
                self.logger.warning(f"Error unloading chat model: {e}")
                self._chat_model = None

    def _unload_tool_manager(self) -> None:
        """Unload the tool manager."""
        if self._tool_manager is not None:
            self.logger.debug("Unloading tool manager")
            try:
                del self._tool_manager
                self._tool_manager = None
            except Exception as e:
                self.logger.warning(f"Error unloading tool manager: {e}")
                self._tool_manager = None

    def _unload_workflow_manager(self) -> None:
        """Unload the workflow manager."""
        if self._workflow_manager is not None:
            self.logger.debug("Unloading workflow manager")
            try:
                del self._workflow_manager
                self._workflow_manager = None
            except Exception as e:
                self.logger.warning(f"Error unloading workflow manager: {e}")
                self._workflow_manager = None

    def _unload_model(self) -> None:
        """
        Unload the LLM model from memory.

        Sets self._model to None after unloading.
        """
        self.logger.debug("Unloading model")
        try:
            if self._model is not None:
                del self._model
                self._model = None
                # Force garbage collection
                gc.collect()
        except AttributeError as e:
            self.logger.warning(f"Error unloading model: {e}")
            self._model = None

    def _unload_tokenizer(self) -> None:
        """
        Unload the tokenizer from memory.

        Sets self._tokenizer to None after unloading.
        """
        self.logger.debug("Unloading tokenizer")
        try:
            if self._tokenizer is not None:
                del self._tokenizer
                self._tokenizer = None
        except AttributeError as e:
            self.logger.warning(f"Error unloading tokenizer: {e}")
            self._tokenizer = None

    def _do_generate(
        self,
        prompt: str,
        action: LLMActionType,
        system_prompt: Optional[str] = None,
        rag_system_prompt: Optional[str] = None,
        llm_request: Optional[Any] = None,
        do_tts_reply: bool = True,
        extra_context: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Generate a response using the loaded LLM.

        This method handles the core generation process, including:
        - Checking if model reload is needed
        - Streaming from the workflow manager
        - Sending response signals

        Args:
            prompt: The text prompt for generation.
            action: The type of action to perform.
            system_prompt: Optional system prompt to override defaults.
            rag_system_prompt: Optional system prompt for RAG operations.
            llm_request: Optional request configuration.
            do_tts_reply: Whether to convert the reply to speech.
            extra_context: Dictionary of context keyed by unique identifier (e.g., URL, file path).

        Returns:
            Dict: Dictionary with generation results.
        """
        self.logger.debug(f"Generating response for action: {action}")

        # Reload model if path changed
        if self._current_model_path != self.model_path:
            self.unload()
            self.load()

        # Use code defaults (not database) for better repetition handling
        llm_request = llm_request or LLMRequest()

        # Update workflow system prompt based on action
        action_system_prompt = (
            system_prompt
            if system_prompt
            else self.get_system_prompt_for_action(action)
        )
        if self._workflow_manager:
            self._workflow_manager.update_system_prompt(action_system_prompt)
            self.logger.debug(
                f"Updated workflow system prompt for action {action}"
            )

        # Stream from workflow manager
        complete_response = ""
        try:
            for message in self._workflow_manager.stream(prompt):
                if isinstance(message, AIMessage) and message.content:
                    chunk = message.content
                    complete_response += chunk

                    # Send streaming response
                    self.api.llm.send_llm_text_streamed_signal(
                        LLMResponse(
                            node_id=(
                                llm_request.node_id if llm_request else None
                            ),
                            message=chunk,
                            is_end_of_message=False,
                        )
                    )
        except Exception as e:
            self.logger.error(f"Error during generation: {e}", exc_info=True)
            complete_response = f"Error: {str(e)}"

        # Send final message
        if action is LLMActionType.CHAT:
            self._send_final_message(llm_request)

        return {"response": complete_response}

    def _send_final_message(
        self, llm_request: Optional[LLMRequest] = None
    ) -> None:
        """
        Send a signal indicating the end of a message stream.

        This helps clients know when a complete response has been delivered.
        """
        self.logger.debug("Sending final message")
        self.api.llm.send_llm_text_streamed_signal(
            LLMResponse(
                node_id=llm_request.node_id if llm_request else None,
                is_end_of_message=True,
            )
        )

    def _do_set_seed(self) -> None:
        """
        Set random seeds for deterministic generation.

        This ensures reproducible results when using the same seed.
        """
        self.logger.debug("Setting seed")

        # Get seed from settings
        if self.llm_generator_settings.override_parameters:
            seed = self.llm_generator_settings.seed
            random_seed = self.llm_generator_settings.random_seed
        else:
            seed = self.chatbot.seed
            random_seed = self.chatbot.random_seed

        # Generate random seed if needed
        if random_seed:
            seed = random.randint(-AIRUNNER_MAX_SEED, AIRUNNER_MAX_SEED)

        # Set seeds for all relevant components
        torch.manual_seed(seed)
        torch.cuda.manual_seed(seed)
        torch.cuda.manual_seed_all(seed)
        random.seed(seed)

        # Configure deterministic behavior
        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark = False

        # Set tokenizer seed if available
        if self._tokenizer:
            self._tokenizer.seed = seed
