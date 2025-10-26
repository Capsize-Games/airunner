import gc
import random
import os
import json
import traceback
import torch
from datetime import datetime
from typing import Optional, Dict, Any, List, Union

from peft import PeftModel
from transformers.utils.quantization_config import (
    BitsAndBytesConfig,
    GPTQConfig,
)
from transformers import (
    AutoModel,
    AutoModelForCausalLM,
    AutoTokenizer,
    AutoConfig,
)
from transformers.generation.streamers import TextIteratorStreamer
from langchain_core.messages import AIMessage

try:
    from transformers.models.mistral3 import Mistral3ForConditionalGeneration
except ImportError:
    Mistral3ForConditionalGeneration = None

from airunner.components.conversations.conversation_history_manager import (
    ConversationHistoryManager,
)
from airunner.components.llm.config.provider_config import LLMProviderConfig
from airunner.components.llm.config.model_capabilities import ModelCapability
from airunner.components.llm.data.conversation import Conversation
from airunner.components.llm.data.fine_tuned_model import FineTunedModel
from airunner.components.application.managers.base_model_manager import (
    BaseModelManager,
)
from airunner.components.llm.adapters import ChatModelFactory
from airunner.components.llm.managers.tool_manager import ToolManager
from airunner.components.llm.managers.workflow_manager import WorkflowManager
from airunner.components.llm.managers.quantization_mixin import (
    QuantizationMixin,
)
from airunner.components.llm.managers.mixins import (
    ConversationManagementMixin,
    QuantizationConfigMixin,
    StatusManagementMixin,
    TokenizerLoaderMixin,
    ValidationMixin,
)
from airunner.components.llm.managers.training_mixin import TrainingMixin
from airunner.components.llm.managers.agent.rag_mixin import RAGMixin
from airunner.components.model_management.hardware_profiler import (
    HardwareProfiler,
)
from airunner.components.model_management.model_resource_manager import (
    ModelResourceManager,
)
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
from airunner.components.llm.managers.llm_request import LLMRequest
from airunner.components.llm.managers.llm_response import LLMResponse
from airunner.components.llm.managers.llm_settings import LLMSettings


class LLMModelManager(
    BaseModelManager,
    ConversationManagementMixin,
    QuantizationConfigMixin,
    StatusManagementMixin,
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

    @property
    def supports_function_calling(self) -> bool:
        """Check if the current model supports function calling."""
        try:
            model_path = self.model_path
            if not model_path:
                return False

            for (
                model_key,
                model_info,
            ) in LLMProviderConfig.LOCAL_MODELS.items():
                if model_key in model_path or model_info["name"] in model_path:
                    return model_info.get("function_calling", False)

            return False
        except Exception as e:
            self.logger.warning(
                f"Could not determine function calling support: {e}"
            )
            return False

    @property
    def system_prompt(self) -> str:
        """Generate the system prompt for the LLM."""
        parts = []

        if hasattr(self, "chatbot") and self.chatbot:
            parts.append(
                f"You are {self.chatbot.botname}, a helpful AI assistant."
            )

            if (
                hasattr(self.chatbot, "personality")
                and self.chatbot.personality
            ):
                parts.append(f"Personality: {self.chatbot.personality}")
        else:
            parts.append("You are a helpful AI assistant.")

        now = datetime.now()
        parts.append(
            f"Current date and time: {now.strftime('%Y-%m-%d %H:%M:%S')}"
        )

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

    def _get_available_vram_gb(self) -> float:
        """Get available VRAM in gigabytes."""
        if not hasattr(self, "_hw_profiler"):
            self._hw_profiler = HardwareProfiler()
        return self._hw_profiler._get_available_vram_gb()

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
        """Extract model name from model path."""
        if not self.llm_generator_settings.model_path:
            raise ValueError(
                "No model path configured. Please select a model in LLM settings."
            )
        return os.path.basename(
            os.path.normpath(self.llm_generator_settings.model_path)
        )

    @property
    def llm(self):
        """
        Get the LlamaIndex-compatible LLM wrapper for RAG.

        This property is required by RAGMixin to initialize the RAG system.
        Returns None if the chat model hasn't been loaded yet.

        Returns:
            LlamaIndex LLM wrapper or None
        """
        if self._chat_model is None:
            return None

        # LlamaIndex needs a LlamaIndex-compatible LLM, not a LangChain one
        # For now, return the LangChain chat model and let LlamaIndex handle conversion
        # If this causes issues, we'll need to wrap it properly
        try:
            from llama_index.llms.langchain import LangChainLLM

            return LangChainLLM(llm=self._chat_model)
        except Exception:
            # If LlamaIndex LangChain adapter isn't available, return the chat model
            # and hope LlamaIndex can work with it directly
            return self._chat_model

    @property
    def model_path(self) -> str:
        """
        Get the filesystem path to the model files from settings.

        Returns:
            str: Absolute path to the model directory.

        Raises:
            ValueError: If no model path is configured in settings.
        """
        if not self.llm_generator_settings.model_path:
            raise ValueError(
                "No model path configured. Please select a model in LLM settings."
            )
        return os.path.expanduser(self.llm_generator_settings.model_path)

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

    def load_specialized_model(
        self,
        capability: "ModelCapability",
        return_to_primary: bool = True,
    ) -> Optional[Any]:
        """
        Load a specialized model for a specific task.

        This method is used by tools to load specialized models (e.g., prompt
        enhancer, code generator) for specific tasks. It handles model swapping
        through the resource manager and can optionally return to the primary
        model after the task completes.

        Args:
            capability: The capability needed (from ModelCapability enum)
            return_to_primary: Whether to swap back to primary model after use

        Returns:
            The loaded chat model, or None if loading failed

        Example:
            # In a tool:
            from airunner.components.llm.config.model_capabilities import ModelCapability

            manager = LLMModelManager()
            model = manager.load_specialized_model(
                ModelCapability.PROMPT_ENHANCEMENT
            )
            if model:
                enhanced = model.invoke("Enhance this: " + prompt)
                # Model auto-swaps back to primary after this method returns
        """
        from airunner.components.llm.config.model_capabilities import (
            get_model_for_capability,
        )

        # Get the model spec for this capability
        model_spec = get_model_for_capability(capability)
        if not model_spec:
            self.logger.warning(
                f"No model registered for capability: {capability}"
            )
            return None

        # Store the current primary model info
        if return_to_primary:
            primary_model_path = self._current_model_path or self.model_path

        # Check if we're already using the right model
        current_path = self._current_model_path or self.model_path
        if current_path == model_spec.model_path:
            self.logger.info(
                f"Already using {model_spec.model_path} for {capability}"
            )
            return self._chat_model

        # Use resource manager to swap models
        self.logger.info(
            f"Loading specialized model {model_spec.model_path} for {capability}"
        )

        # Unload current model
        self.unload()

        # Temporarily override model path
        original_model_path = self.llm_generator_settings.model_path
        self.llm_generator_settings.model_path = model_spec.model_path

        try:
            # Load the specialized model
            self.load()

            if return_to_primary:
                # Store function to restore primary model
                self._restore_primary_model = lambda: self._do_restore_primary(
                    primary_model_path, original_model_path
                )

            return self._chat_model

        except Exception as e:
            self.logger.error(
                f"Failed to load specialized model: {e}", exc_info=True
            )
            # Restore original settings
            self.llm_generator_settings.model_path = original_model_path
            return None

    def _do_restore_primary(
        self, primary_model_path: str, original_setting: str
    ) -> None:
        """Internal helper to restore primary model."""
        self.logger.info(f"Restoring primary model: {primary_model_path}")
        self.unload()
        self.llm_generator_settings.model_path = original_setting
        self.load()
        self._restore_primary_model = None

    def use_specialized_model(
        self,
        capability: "ModelCapability",
        prompt: str,
        max_tokens: int = 512,
    ) -> Optional[str]:
        """
        Convenience method to use a specialized model for a single generation.

        This loads the specialized model, generates a response, and automatically
        swaps back to the primary model.

        Args:
            capability: The capability needed
            prompt: The prompt to send to the specialized model
            max_tokens: Maximum tokens to generate

        Returns:
            Generated text, or None if generation failed

        Example:
            # In a tool:
            manager = LLMModelManager()
            enhanced_prompt = manager.use_specialized_model(
                ModelCapability.PROMPT_ENHANCEMENT,
                "Enhance this Stable Diffusion prompt: a cat"
            )
        """
        model = self.load_specialized_model(capability, return_to_primary=True)
        if not model:
            return None

        try:
            # Generate with the specialized model
            response = model.invoke(prompt)

            # Extract text from response
            if isinstance(response, AIMessage):
                result = response.content
            elif isinstance(response, str):
                result = response
            else:
                result = str(response)

            # Restore primary model if needed
            if (
                hasattr(self, "_restore_primary_model")
                and self._restore_primary_model
            ):
                self._restore_primary_model()

            return result

        except Exception as e:
            self.logger.error(
                f"Failed to generate with specialized model: {e}",
                exc_info=True,
            )
            # Try to restore primary model even on error
            if (
                hasattr(self, "_restore_primary_model")
                and self._restore_primary_model
            ):
                try:
                    self._restore_primary_model()
                except Exception as restore_error:
                    self.logger.error(
                        f"Failed to restore primary model: {restore_error}"
                    )
            return None

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
        pass

    def _log_gpu_memory_status(self) -> None:
        """Log current GPU memory usage."""
        if not torch.cuda.is_available():
            return

        torch.cuda.empty_cache()
        gc.collect()
        free_memory = torch.cuda.mem_get_info()[0] / (1024**3)
        total_memory = torch.cuda.get_device_properties(0).total_memory / (
            1024**3
        )
        self.logger.info(
            f"GPU memory before loading: {free_memory:.2f}GB free / {total_memory:.2f}GB total"
        )

    def _detect_mistral3_model(self, config: AutoConfig) -> bool:
        """Check if model configuration indicates Mistral3 architecture."""
        is_mistral3_type = (
            hasattr(config, "model_type") and config.model_type == "mistral3"
        )
        is_mistral3_arch = hasattr(config, "architectures") and any(
            "Mistral3" in arch for arch in (config.architectures or [])
        )
        return is_mistral3_type or is_mistral3_arch

    def _prepare_base_model_kwargs(self, is_mistral3: bool) -> Dict[str, Any]:
        """Prepare base kwargs for model loading."""
        model_kwargs = {
            "local_files_only": AIRUNNER_LOCAL_FILES_ONLY,
            "trust_remote_code": True,
            "attn_implementation": self.attn_implementation,
        }

        if not is_mistral3:
            model_kwargs["use_cache"] = self.use_cache

        return model_kwargs

    def _apply_quantization_to_kwargs(
        self,
        model_kwargs: Dict[str, Any],
        quantization_config: Optional[BitsAndBytesConfig],
        dtype: str,
    ) -> None:
        """Apply quantization configuration to model kwargs."""
        if quantization_config is None:
            model_kwargs["torch_dtype"] = self.torch_dtype
            model_kwargs["device_map"] = self.device
            self.logger.warning(
                "No quantization config - loading in full precision!"
            )
            return

        model_kwargs["quantization_config"] = quantization_config
        model_kwargs["device_map"] = "auto"
        model_kwargs["dtype"] = self.torch_dtype

        max_memory = self._configure_quantization_memory(dtype)
        if max_memory:
            model_kwargs["max_memory"] = max_memory

    def _load_model_from_pretrained(
        self, model_path: str, is_mistral3: bool, model_kwargs: Dict[str, Any]
    ) -> None:
        """Load model from pretrained weights."""
        if is_mistral3:
            self._load_mistral3_model(model_path, model_kwargs)
        else:
            self._load_standard_model(model_path, model_kwargs)

    def _load_mistral3_model(
        self, model_path: str, model_kwargs: Dict[str, Any]
    ) -> None:
        """Load Mistral3 model."""
        self.logger.info(
            "Loading Mistral3 model with Mistral3ForConditionalGeneration"
        )
        if Mistral3ForConditionalGeneration is None:
            raise ImportError(
                "Mistral3ForConditionalGeneration not available. "
                "Ensure transformers supports Mistral3 models."
            )
        self._model = Mistral3ForConditionalGeneration.from_pretrained(
            model_path, **model_kwargs
        )
        self.logger.info("✓ Mistral3 model loaded successfully")

    def _load_standard_model(
        self, model_path: str, model_kwargs: Dict[str, Any]
    ) -> None:
        """Load standard causal LM model with fallback."""
        try:
            self._model = AutoModelForCausalLM.from_pretrained(
                model_path, **model_kwargs
            )
        except ValueError as ve:
            if "Unrecognized configuration class" in str(ve):
                self.logger.warning(
                    f"AutoModelForCausalLM doesn't recognize model architecture: {type(ve).__name__}"
                )
                self.logger.info(
                    "Falling back to AutoModel.from_pretrained() for custom architecture"
                )
                self._model = AutoModel.from_pretrained(
                    model_path, **model_kwargs
                )
            else:
                raise

    def _load_model(self) -> None:
        """Load the LLM model with appropriate quantization."""
        if self._model is not None:
            return

        self._log_gpu_memory_status()

        try:
            dtype = self._select_dtype()

            # Check if a pre-quantized model exists on disk
            quantized_path = self._get_quantized_model_path(
                self.model_path, dtype
            )

            if dtype in [
                "4bit",
                "8bit",
            ] and self._check_quantized_model_exists(quantized_path):
                self.logger.info(
                    f"✓ Found existing {dtype} quantized model at {quantized_path}"
                )
                self._load_pre_quantized_model(quantized_path, dtype)
            else:
                # No pre-quantized model - load with runtime quantization
                if dtype in ["4bit", "8bit"]:
                    self.logger.info(
                        f"No pre-quantized {dtype} model found - will quantize at runtime and save"
                    )
                self._load_with_runtime_quantization(dtype)

            self._load_adapters()

        except Exception as e:
            self.logger.error(
                f"Error loading model: {type(e).__name__}: {str(e)}"
            )
            self.logger.error(f"Model traceback:\n{traceback.format_exc()}")
            self._model = None

    def _load_pre_quantized_model(
        self, quantized_path: str, dtype: str
    ) -> None:
        """
        Load a pre-saved BitsAndBytes quantized model from disk.

        The saved config.json already contains the quantization_config,
        so transformers will automatically recognize it's quantized.
        We must NOT pass a quantization_config here, as that would try
        to re-quantize already-quantized weights (causing uint8 error).
        """
        self.logger.info(
            f"Loading pre-saved {dtype} quantized model from {quantized_path}"
        )

        config = AutoConfig.from_pretrained(
            quantized_path,
            local_files_only=AIRUNNER_LOCAL_FILES_ONLY,
            trust_remote_code=True,
        )

        is_mistral3 = self._detect_mistral3_model(config)
        model_kwargs = self._prepare_base_model_kwargs(is_mistral3)

        # Don't pass quantization_config - it's already in the saved config.json
        # Just set device_map and dtype for loading
        model_kwargs["device_map"] = "auto"
        model_kwargs["torch_dtype"] = self.torch_dtype

        self._load_model_from_pretrained(
            quantized_path, is_mistral3, model_kwargs
        )

        self.logger.info(
            f"✓ Pre-quantized {dtype} model loaded successfully from disk"
        )

    def _load_with_runtime_quantization(self, dtype: str) -> None:
        """Load model with runtime BitsAndBytes quantization."""
        quantization_config = self._create_bitsandbytes_config(dtype)

        model_path = self.model_path
        config = AutoConfig.from_pretrained(
            model_path,
            local_files_only=AIRUNNER_LOCAL_FILES_ONLY,
            trust_remote_code=True,
        )

        is_mistral3 = self._detect_mistral3_model(config)
        model_kwargs = self._prepare_base_model_kwargs(is_mistral3)
        self._apply_quantization_to_kwargs(
            model_kwargs, quantization_config, dtype
        )
        self._load_model_from_pretrained(model_path, is_mistral3, model_kwargs)

        # Save quantized model for faster future loads
        # We need to manually inject quantization_config into config.json
        if dtype in ["4bit", "8bit"]:
            try:
                self.logger.info(
                    f"Saving {dtype} quantized model for faster future loads..."
                )
                self._save_loaded_model_quantized(
                    model_path, dtype, quantization_config
                )
            except Exception as e:
                self.logger.warning(
                    f"Could not save quantized model: {e}. "
                    f"Will use runtime quantization on next load."
                )

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
        try:
            adapters = FineTunedModel.objects.all()
            return [a for a in adapters if a.name in adapter_names]
        except Exception as e:
            # Table might not exist if migrations haven't run
            self.logger.error(f"Error querying adapters: {e}")
            return []

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

            rag_manager = getattr(self, "rag_manager", None)

            self._chat_model = ChatModelFactory.create_from_settings(
                llm_settings=self.llm_settings,
                model=self._model,
                tokenizer=self._tokenizer,
                chatbot=getattr(self, "chatbot", None),
                model_path=self._current_model_path,
            )

            self.logger.info(
                f"ChatModel created: {type(self._chat_model).__name__}"
            )

            # Now that chat model is loaded, initialize RAG system
            # RAGMixin._setup_rag() checks if llm is available
            if hasattr(self, "_setup_rag"):
                self.logger.info(
                    "Initializing RAG system now that LLM is loaded"
                )
                self._setup_rag()

        except Exception as e:
            self.logger.error(f"Error creating ChatModel: {e}", exc_info=True)
            self._chat_model = None

    def _load_tool_manager(self) -> None:
        """Load the tool manager."""
        if self._tool_manager is not None:
            return

        try:
            # Pass self as rag_manager since LLMModelManager now inherits RAGMixin
            # This gives tools access to the active document indexes
            self._tool_manager = ToolManager(rag_manager=self)
            self.logger.info("Tool manager loaded with RAG capabilities")
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

            # Otherwise, keep tools=None to avoid injecting tool schemas
            tools_to_use = None
            if self.supports_function_calling and self.tools:
                tools_to_use = self.tools
                self.logger.info(
                    f"Model supports function calling - passing {len(self.tools)} tools"
                )
            else:
                if not self.supports_function_calling:
                    self.logger.info(
                        "Model does not support function calling - no tools will be passed"
                    )
                else:
                    self.logger.info(
                        "No tools available - workflow will run without tools"
                    )

            # The conversation ID will be set explicitly when needed
            self._workflow_manager = WorkflowManager(
                system_prompt=self.system_prompt,
                chat_model=self._chat_model,
                tools=tools_to_use,
                max_tokens=2000,
                conversation_id=None,
            )
            self.logger.info(
                "Workflow manager loaded (conversation ID will be set on first use)"
            )
        except Exception as e:
            self.logger.error(
                f"Error loading workflow manager: {e}", exc_info=True
            )
            self._workflow_manager = None

    def _unload_chat_model(self) -> None:
        """Unload the chat model from memory."""
        if self._chat_model is not None:
            try:
                del self._chat_model
                self._chat_model = None
            except Exception as e:
                self.logger.warning(f"Error unloading chat model: {e}")
                self._chat_model = None

    def _unload_tool_manager(self) -> None:
        """Unload the tool manager."""
        if self._tool_manager is not None:
            try:
                del self._tool_manager
                self._tool_manager = None
            except Exception as e:
                self.logger.warning(f"Error unloading tool manager: {e}")
                self._tool_manager = None

    def _unload_workflow_manager(self) -> None:
        """Unload the workflow manager."""
        if self._workflow_manager is not None:
            try:
                del self._workflow_manager
                self._workflow_manager = None
            except Exception as e:
                self.logger.warning(f"Error unloading workflow manager: {e}")
                self._workflow_manager = None

    def _unload_model(self) -> None:
        """Unload the LLM model from memory."""
        try:
            if self._model is not None:
                del self._model
                self._model = None
                gc.collect()

                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                    torch.cuda.synchronize()
        except AttributeError as e:
            self.logger.warning(f"Error unloading model: {e}")
            self._model = None

    def _unload_tokenizer(self) -> None:
        """Unload the tokenizer from memory."""
        try:
            if self._tokenizer is not None:
                del self._tokenizer
                self._tokenizer = None
                gc.collect()
        except AttributeError as e:
            self.logger.warning(f"Error unloading tokenizer: {e}")
            self._tokenizer = None

    def _setup_generation_workflow(
        self, action: LLMActionType, system_prompt: Optional[str]
    ) -> str:
        """Configure workflow with system prompt and tools for the action.

        Returns:
            The action-specific system prompt
        """
        action_system_prompt = (
            system_prompt
            if system_prompt
            else self.get_system_prompt_for_action(action)
        )

        if self._workflow_manager:
            self._workflow_manager.update_system_prompt(action_system_prompt)

            if self._tool_manager:
                action_tools = self._tool_manager.get_tools_for_action(action)
                self._workflow_manager.update_tools(action_tools)

        return action_system_prompt

    def _create_streaming_callback(
        self,
        llm_request: Optional[Any],
        complete_response: List[str],
        sequence_counter: List[int],
    ):
        """Create callback function for streaming tokens.

        Args:
            llm_request: The LLM request object
            complete_response: List with single string element for response accumulation
            sequence_counter: List with single int element for sequence tracking
        """

        def handle_streaming_token(token_text: str) -> None:
            """Forward streaming tokens to the GUI and accumulate response."""
            if not token_text:
                return
            complete_response[0] += token_text
            sequence_counter[0] += 1
            self.api.llm.send_llm_text_streamed_signal(
                LLMResponse(
                    node_id=llm_request.node_id if llm_request else None,
                    message=token_text,
                    is_end_of_message=False,
                    is_first_message=(sequence_counter[0] == 1),
                    sequence_number=sequence_counter[0],
                )
            )

        return handle_streaming_token

    def _handle_interrupted_generation(
        self, llm_request: Optional[Any], sequence_counter: int
    ) -> str:
        """Handle interrupted generation.

        Returns:
            Interruption message
        """
        self.logger.info("Generation interrupted by user")
        interrupt_msg = "\n\n[Generation interrupted]"
        self.api.llm.send_llm_text_streamed_signal(
            LLMResponse(
                node_id=llm_request.node_id if llm_request else None,
                message=interrupt_msg,
                is_end_of_message=True,
                sequence_number=sequence_counter + 1,
            )
        )
        return interrupt_msg

    def _handle_generation_error(
        self, exc: Exception, llm_request: Optional[Any]
    ) -> str:
        """Handle generation error.

        Returns:
            Error message
        """
        self.logger.error(f"Error during generation: {exc}", exc_info=True)
        error_message = f"Error: {exc}"
        self.api.llm.send_llm_text_streamed_signal(
            LLMResponse(
                node_id=llm_request.node_id if llm_request else None,
                message=error_message,
                is_end_of_message=False,
            )
        )
        return error_message

    def _extract_final_response(self, result: Dict[str, Any]) -> str:
        """Extract final response from generation result.

        Returns:
            Final response content or empty string
        """
        if not result or "messages" not in result:
            return ""

        final_messages = [
            message
            for message in result["messages"]
            if isinstance(message, AIMessage)
        ]

        if final_messages:
            final_content = final_messages[-1].content or ""
            if final_content:
                return final_content

        return ""

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
        """Generate a response using the loaded LLM."""
        if self._current_model_path != self.model_path:
            self.logger.warning(
                f"Model path mismatch detected: "
                f"current='{self._current_model_path}' vs settings='{self.model_path}'. "
                f"Reloading model..."
            )
            self.unload()
            self.load()

        llm_request = llm_request or LLMRequest()
        self._setup_generation_workflow(action, system_prompt)

        complete_response = [""]
        sequence_counter = [0]
        self._interrupted = False

        if not self._workflow_manager:
            self.logger.error("Workflow manager is not initialized")
            return {"response": "Error: workflow unavailable"}

        callback = self._create_streaming_callback(
            llm_request, complete_response, sequence_counter
        )
        self._workflow_manager.set_token_callback(callback)

        # Reset workflow manager's interrupted flag before generation
        if hasattr(self._workflow_manager, "set_interrupted"):
            self._workflow_manager.set_interrupted(False)

        try:
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                torch.cuda.synchronize()

            # CRITICAL: Use stream() instead of invoke() to allow interrupt checking
            # invoke() is completely blocking and ignores interrupt flags
            # stream() checks the interrupt flag on each token, allowing fast response

            # Prepare generation kwargs from LLMRequest
            generation_kwargs = llm_request.to_dict() if llm_request else {}
            # Remove non-generation parameters
            for key in [
                "do_tts_reply",
                "use_cache",
                "node_id",
                "use_memory",
                "role",
            ]:
                generation_kwargs.pop(key, None)

            result_messages = []
            for message in self._workflow_manager.stream(
                prompt, generation_kwargs
            ):
                # Check interrupt flag during streaming
                if self._interrupted:
                    self.logger.info(
                        "Stream interrupted - breaking out of generation"
                    )
                    break
                result_messages.append(message)

            # Convert streamed messages to result format
            result = {"messages": result_messages}

            if self._interrupted:
                interrupt_msg = self._handle_interrupted_generation(
                    llm_request, sequence_counter[0]
                )
                complete_response[0] += interrupt_msg
                result = {"messages": []}
        except Exception as exc:
            error_msg = self._handle_generation_error(exc, llm_request)
            complete_response[0] = error_msg
            result = {"messages": []}
        finally:
            self._workflow_manager.set_token_callback(None)
            self._interrupted = False
            if hasattr(self._workflow_manager, "set_interrupted"):
                self._workflow_manager.set_interrupted(False)

        final_response = self._extract_final_response(result)
        if final_response:
            complete_response[0] = final_response

        sequence_counter[0] += 1
        self.api.llm.send_llm_text_streamed_signal(
            LLMResponse(
                node_id=llm_request.node_id if llm_request else None,
                is_end_of_message=True,
                sequence_number=sequence_counter[0],
            )
        )

        return {"response": complete_response[0]}

    def _send_final_message(
        self, llm_request: Optional[LLMRequest] = None
    ) -> None:
        """Send a signal indicating the end of a message stream."""
        self.api.llm.send_llm_text_streamed_signal(
            LLMResponse(
                node_id=llm_request.node_id if llm_request else None,
                is_end_of_message=True,
            )
        )

    def _do_set_seed(self) -> None:
        """Set random seeds for deterministic generation."""
        if self.llm_generator_settings.override_parameters:
            seed = self.llm_generator_settings.seed
            random_seed = self.llm_generator_settings.random_seed
        else:
            seed = self.chatbot.seed
            random_seed = self.chatbot.random_seed

        if random_seed:
            seed = random.randint(-AIRUNNER_MAX_SEED, AIRUNNER_MAX_SEED)

        torch.manual_seed(seed)
        torch.cuda.manual_seed(seed)
        torch.cuda.manual_seed_all(seed)
        random.seed(seed)

        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark = False

        if self._tokenizer:
            self._tokenizer.seed = seed
