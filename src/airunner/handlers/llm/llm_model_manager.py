import random
import os
import torch
from typing import Optional, Dict, List, Union, Type

from peft import PeftModel
from transformers.utils.quantization_config import (
    BitsAndBytesConfig,
    GPTQConfig,
)
from transformers import AutoModelForCausalLM, AutoTokenizer
from transformers.generation.streamers import TextIteratorStreamer
from llama_index.core.chat_engine.types import AgentChatResponse

from airunner.handlers.base_model_manager import BaseModelManager
from airunner.enums import (
    ModelType,
    ModelStatus,
    LLMActionType,
)
from airunner.utils import is_windows
from airunner.settings import (
    AIRUNNER_MAX_SEED,
    AIRUNNER_LOCAL_FILES_ONLY,
)
from airunner.utils.memory import clear_memory
from airunner.handlers.llm.agent.agents import LocalAgent, OpenRouterQObject
from airunner.data.models import Conversation, LLMGeneratorSettings
from airunner.handlers.llm.training_mixin import TrainingMixin
from airunner.handlers.llm.llm_request import LLMRequest
from airunner.handlers.llm.llm_response import LLMResponse
from airunner.handlers.llm.llm_settings import LLMSettings


class LLMModelManager(BaseModelManager, TrainingMixin):
    """
    Handler for Large Language Model operations in AI Runner.

    This class manages the lifecycle of LLM models, including loading, unloading,
    and generating responses. It supports both local LLMs and API-based LLMs,
    and integrates with various agent types.

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

    # Agent components
    _chat_agent: Optional[Union[Type[LocalAgent], OpenRouterQObject]] = None
    _agent_executor: Optional[object] = None
    _service_context_model: Optional[object] = None

    # Agent configuration
    _use_query_engine: bool = False
    _use_chat_engine: bool = True
    _user_evaluation: str = ""
    _restrict_tools_to_additional: bool = True
    _return_agent_code: bool = False

    # RAG components
    _rag_tokenizer: Optional[object] = None
    _rag_retriever: Optional[object] = None

    # Other components
    _vocoder: Optional[object] = None
    _generator: Optional[object] = None
    _history: Optional[List] = []

    # Settings
    llm_settings: LLMSettings

    def __init__(
        self,
        local_agent_class: Optional[Type[LocalAgent]] = None,
        *args,
        **kwargs,
    ):
        """
        Initialize the LLM handler.

        Args:
            local_agent_class: Class to use for local agent implementation.
                              Defaults to LocalAgent if None.
            *args: Variable length argument list passed to parent classes.
            **kwargs: Arbitrary keyword arguments passed to parent classes.
        """
        self.local_agent_class_ = local_agent_class or LocalAgent
        super().__init__(*args, **kwargs)
        # Initialize the instance status *after* the base class init
        self._model_status = {ModelType.LLM: ModelStatus.UNLOADED}
        self.llm_settings = LLMSettings()

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
                "causallm",
                "w4ffl35/Ministral-8B-Instruct-2410-doublequant",
            )
        )

    def load(self) -> None:
        """
        Load the LLM model and associated components.

        This method handles the complete loading process, including:
        - Checking if the model is already loaded
        - Loading the tokenizer and model if using a local LLM
        - Loading the appropriate chat agent
        - Updating the model status based on loading results
        """
        # Skip if already loading or loaded
        if self.model_status[ModelType.LLM] in (
            ModelStatus.LOADING,
            ModelStatus.LOADED,
        ):
            return

        # Start loading process
        self.unload()
        self.change_model_status(ModelType.LLM, ModelStatus.LOADING)
        self._current_model_path = self.model_path

        # Load components based on settings
        self._load_tokenizer()
        self._load_model()
        self._load_agent()
        self._update_model_status()

    def _update_model_status(self):
        # Update status based on loading results
        if self._model and self._tokenizer and self._chat_agent:
            self.change_model_status(ModelType.LLM, ModelStatus.LOADED)
        else:
            if not self._model:
                self.logger.error("Model failed to load")
            if not self._chat_agent:
                self.logger.error("Chat agent failed to load")
            self.change_model_status(ModelType.LLM, ModelStatus.FAILED)

    def unload(self) -> None:
        """
        Unload all LLM components from memory.

        This method properly releases resources by:
        - Unloading the model, tokenizer, and agent
        - Clearing GPU memory
        - Updating the model status
        """
        # Skip if already unloading or unloaded
        if self.model_status[ModelType.LLM] in (
            ModelStatus.LOADING,
            ModelStatus.UNLOADED,
        ):
            return

        self.logger.debug("Unloading LLM")
        self.change_model_status(ModelType.LLM, ModelStatus.LOADING)

        # Unload components
        self._unload_model()
        self._unload_tokenizer()
        self._unload_agent()

        # Clear GPU memory
        clear_memory(self.device)

        self.change_model_status(ModelType.LLM, ModelStatus.UNLOADED)

    def handle_request(self, data: Dict) -> AgentChatResponse:
        """
        Handle an incoming request for LLM generation.

        Args:
            data: Dictionary containing request parameters, including:
                - request_data.prompt: The text prompt to process
                - request_data.action: The type of action to perform
                - request_data.llm_request: Configuration for the request

        Returns:
            AgentChatResponse: The generated response from the LLM.
        """
        self.logger.debug("Handling request")
        self._do_set_seed()
        self.load()

        return self._do_generate(
            prompt=data["request_data"]["prompt"],
            action=data["request_data"]["action"],
            llm_request=data["request_data"]["llm_request"],
        )

    def do_interrupt(self) -> None:
        """
        Interrupt the ongoing chat process.

        This can be called to stop a generation that is in progress.
        """
        if self._chat_agent:
            self._chat_agent.interrupt_process()

    def on_conversation_deleted(self, data: Dict) -> None:
        """
        Handle conversation deletion event.

        Args:
            data: Information about the deleted conversation.
        """
        if self._chat_agent:
            self._chat_agent.on_conversation_deleted(data)

    def clear_history(self, data: Optional[Dict] = None) -> None:
        """
        Clear the chat history and set up a new conversation.

        Args:
            data: Optional data containing conversation ID or other parameters.
                 If not provided, a new conversation will be created.
        """
        self.logger.debug("Clearing chat history")

        # Initialize data dict if none provided
        if data is None:
            data = {}

        conversation_id = data.get("conversation_id", None)
        llm_generator_settings = LLMGeneratorSettings.objects.first()
        conversation = Conversation.objects.first()

        # Create new conversation if needed
        if not conversation_id:
            conversation = Conversation.create()
            data["conversation_id"] = conversation.id

        # Update settings to use the current conversation
        LLMGeneratorSettings.objects.update(
            llm_generator_settings.id, current_conversation=conversation.id
        )

        # Clear history in the chat agent
        if self._chat_agent:
            self._chat_agent.clear_history(data)

    def add_chatbot_response_to_history(self, message: str) -> None:
        """
        Add a chatbot-generated response to the chat history.

        Args:
            message: The response message to add to history.
        """
        if self._chat_agent:
            self._chat_agent.add_chatbot_response_to_history(message)
        else:
            self.logger.warning("Cannot add response - chat agent not loaded")

    def load_conversation(self, message: Dict) -> None:
        """
        Load an existing conversation into the chat agent.

        Args:
            message: Data containing the conversation to load.
        """
        if self._chat_agent:
            self._chat_agent.on_load_conversation(message)
        else:
            self.logger.warning(
                "Cannot load conversation - chat agent not loaded"
            )

    def reload_rag_engine(self) -> None:
        """
        Reload the Retrieval-Augmented Generation engine.

        This is useful when the underlying documents or settings have changed.
        """
        if self._chat_agent:
            self._chat_agent.reload_rag_engine()
        else:
            self.logger.warning(
                "Cannot reload RAG engine - chat agent not loaded"
            )

    def on_section_changed(self) -> None:
        """
        Handle section change events by resetting the current tab in the chat agent.
        """
        if self._chat_agent:
            self._chat_agent.current_tab = None
        else:
            self.logger.warning(
                "Cannot update section - chat agent not loaded"
            )

    def on_web_browser_page_html(self, content: str) -> None:
        """
        Process HTML content from a web browser page.

        This allows the chat agent to analyze and use web page content in responses.

        Args:
            content: The HTML content of the web page.
        """
        if self._chat_agent:
            self._chat_agent.on_web_browser_page_html(content)
        else:
            self.logger.error("Chat agent not loaded")

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
        """
        Load the LLM model for the selected version.

        Sets self._model to the loaded model instance or None if loading fails.
        Also attempts to load adapters if available.
        """
        # Skip if already loaded
        if self._model is not None:
            return

        self.logger.debug(f"Loading local LLM model from {self.model_path}")
        try:
            # Load the base model
            self._model = AutoModelForCausalLM.from_pretrained(
                self.model_path,
                local_files_only=AIRUNNER_LOCAL_FILES_ONLY,
                use_cache=self.use_cache,
                trust_remote_code=False,
                torch_dtype=self.torch_dtype,
                device_map=self.device,
                attn_implementation=self.attn_implementation,
            )

            if not is_windows():
                # Attempt to load adapter if available
                try:
                    if os.path.exists(self.adapter_path):
                        # Convert base model to PEFT format
                        self._model = PeftModel.from_pretrained(
                            self._model, self.adapter_path
                        )
                        self.logger.info(
                            f"Loaded adapter from {self.adapter_path}"
                        )
                except Exception as e:
                    self.logger.error(
                        f"Error loading adapter (continuing with base model): {e}"
                    )

        except Exception as e:
            self.logger.error(f"Error loading model: {e}")
            self._model = None

    def _load_agent(self) -> None:
        """
        Load the appropriate chat agent based on settings.

        Sets self._chat_agent to the loaded agent instance or None if loading fails.
        """
        # Skip if already loaded
        if self._chat_agent is not None:
            return

        self.logger.info("Loading local chat agent")
        self._chat_agent = self.local_agent_class_(
            model=self._model,
            tokenizer=self._tokenizer,
            default_tool_choice=None,
            llm_settings=self.llm_settings,
        )

        self.logger.info("Chat agent loaded")

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

    def _unload_agent(self) -> None:
        """
        Unload the chat agent from memory.

        Calls the agent's unload method if available, then sets self._chat_agent to None.
        """
        if self._chat_agent is not None:
            self.logger.debug("Unloading chat agent")
            try:
                self._chat_agent.unload()
                del self._chat_agent
                self._chat_agent = None
            except AttributeError as e:
                self.logger.warning(f"Error unloading chat agent: {e}")
                self._chat_agent = None

    def _do_generate(
        self,
        prompt: str,
        action: LLMActionType,
        system_prompt: Optional[str] = None,
        rag_system_prompt: Optional[str] = None,
        llm_request: Optional[LLMRequest] = None,
        do_tts_reply: bool = True,
    ) -> AgentChatResponse:
        """
        Generate a response using the loaded LLM.

        This method handles the core generation process, including:
        - Checking if model reload is needed
        - Calling the appropriate chat agent method
        - Sending final message signals

        Args:
            prompt: The text prompt for generation.
            action: The type of action to perform.
            system_prompt: Optional system prompt to override defaults.
            rag_system_prompt: Optional system prompt for RAG operations.
            llm_request: Optional request configuration.
            do_tts_reply: Whether to convert the reply to speech.

        Returns:
            AgentChatResponse: The generated response.
        """
        self.logger.debug("Generating response")

        # Reload model if path changed
        if self._current_model_path != self.model_path:
            self.unload()
            self.load()

        # Generate response using chat agent
        llm_request = llm_request or LLMRequest.from_default()

        # Call the appropriate chat agent method
        response = self._chat_agent.chat(
            prompt,
            action=action,
            system_prompt=system_prompt,
            rag_system_prompt=rag_system_prompt,
            llm_request=llm_request,  # Pass the object directly
        )

        # Handle the response
        # Send end-of-message signal for chat actions
        if action is LLMActionType.CHAT:
            self._send_final_message(llm_request)

        return response

    def _send_final_message(
        self, llm_request: Optional[LLMRequest] = None
    ) -> None:
        """
        Send a signal indicating the end of a message stream.

        This helps clients know when a complete response has been delivered.
        """
        self.logger.debug("Sending final message")
        self.api.send_llm_text_streamed_signal(
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
