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
from airunner.components.llm.managers.training_mixin import TrainingMixin
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


class LLMModelManager(BaseModelManager, QuantizationMixin, TrainingMixin):
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
        """
        Get available VRAM in gigabytes.

        Returns:
            float: Available VRAM in GB, or 0 if CUDA not available
        """
        if not torch.cuda.is_available():
            return 0.0

        try:
            total_memory = torch.cuda.get_device_properties(0).total_memory
            allocated_memory = torch.cuda.memory_allocated(0)

            available_memory = total_memory - allocated_memory
            available_gb = available_memory / (1024**3)

            return available_gb
        except Exception as e:
            self.logger.warning(f"Could not detect VRAM: {e}")
            return 0.0

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

    def _check_model_exists(self) -> bool:
        """
        Check if the model exists at the expected path with all necessary files.

        Returns:
            bool: True if model exists with all required files, False otherwise
        """
        if not self.llm_settings.use_local_llm:
            # API-based models don't need local files
            return True

        model_path = self.model_path
        if not os.path.exists(model_path):
            self.logger.info(f"Model path does not exist: {model_path}")
            return False

        # tokenizer_config.json is optional - some models use different tokenizer files
        essential_files = ["config.json"]
        safetensors_found = False

        try:
            files_in_dir = os.listdir(model_path)

            for file in files_in_dir:
                if file.endswith(".safetensors"):
                    safetensors_found = True
                    break

            has_essential = all(
                os.path.exists(os.path.join(model_path, f))
                for f in essential_files
            )

            if not has_essential:
                missing = [
                    f
                    for f in essential_files
                    if not os.path.exists(os.path.join(model_path, f))
                ]
                self.logger.info(f"Missing essential files: {missing}")

            if not safetensors_found:
                self.logger.info(
                    f"No .safetensors files found in {model_path}"
                )

            result = has_essential and safetensors_found
            self.logger.info(
                f"Model exists check: {result} (has_essential={has_essential}, safetensors_found={safetensors_found})"
            )
            return result

        except Exception as e:
            self.logger.error(f"Error checking model files: {e}")
            return False

    def _trigger_model_download(self) -> bool:
        """Trigger model download via signal."""
        self.logger.info(
            f"Model not found at {self.model_path}, triggering download"
        )

        repo_id = None
        for model_id, model_info in LLMProviderConfig.LOCAL_MODELS.items():
            if model_info["name"] == self.model_name:
                repo_id = model_info["repo_id"]
                break

        if not repo_id:
            self.logger.error(
                f"Could not find repo_id for model: {self.model_name}"
            )
            return False

        self.emit_signal(
            SignalCode.LLM_MODEL_DOWNLOAD_REQUIRED,
            {
                "model_path": self.model_path,
                "model_name": self.model_name,
                "repo_id": repo_id,
            },
        )

        return False

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

        try:
            _ = self.model_path  # This will raise ValueError if not configured
        except ValueError as e:
            self.logger.error(str(e))
            # Emit an LLMResponse so GUI callbacks receive the expected object
            try:
                self.api.llm.send_llm_text_streamed_signal(
                    LLMResponse(message=f"❌ {str(e)}", is_end_of_message=True)
                )
            except Exception:
                # Fallback to the raw emit if api.llm is not available
                self.emit_signal(
                    SignalCode.LLM_TEXT_STREAMED_SIGNAL,
                    {
                        "response": LLMResponse(
                            message=f"❌ {str(e)}", is_end_of_message=True
                        )
                    },
                )
            self.change_model_status(ModelType.LLM, ModelStatus.FAILED)
            return

        if self.llm_settings.use_local_llm and not self._check_model_exists():
            if self.model_status[ModelType.LLM] != ModelStatus.FAILED:
                self._trigger_model_download()
                self.change_model_status(ModelType.LLM, ModelStatus.FAILED)
            return

        self.change_model_status(ModelType.LLM, ModelStatus.LOADING)
        self.unload()
        self._current_model_path = self.model_path

        if self.llm_settings.use_local_llm:
            vram_gb = self._get_available_vram_gb()
            quant_info = self._get_quantization_info(vram_gb)

            self.emit_signal(
                SignalCode.LLM_TEXT_STREAMED_SIGNAL,
                {
                    "response": LLMResponse(
                        message=f"🔧 Auto-selecting quantization: {quant_info['level']} "
                        f"({quant_info['description']}) based on {vram_gb:.1f}GB available VRAM\n",
                        is_end_of_message=False,
                        action=LLMActionType.CHAT,
                    )
                },
            )

        if self.llm_settings.use_local_llm:
            # Local HuggingFace: load model and tokenizer first
            self._load_tokenizer()
            self._load_model()

        self._load_chat_model()

        self._load_tool_manager()
        self._load_workflow_manager()

        self._update_model_status()

    def _update_model_status(self):
        """Update model status based on what's loaded."""
        is_api = self.llm_settings.use_api

        needs_model_and_tokenizer = self.llm_settings.use_local_llm

        if is_api:
            # API mode: just need chat_model and workflow_manager
            if self._chat_model and self._workflow_manager:
                self.change_model_status(ModelType.LLM, ModelStatus.LOADED)
                self.emit_signal(
                    SignalCode.TOGGLE_LLM_SIGNAL, {"enabled": True}
                )
                try:
                    self.api.llm.send_llm_text_streamed_signal(
                        LLMResponse(
                            message="✅ Model loaded successfully (API mode)\n",
                            is_end_of_message=False,
                        )
                    )
                except Exception:
                    self.emit_signal(
                        SignalCode.LLM_TEXT_STREAMED_SIGNAL,
                        {
                            "response": LLMResponse(
                                message="✅ Model loaded successfully (API mode)\n",
                                is_end_of_message=False,
                            )
                        },
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

                # Inform user of successful loading
                try:
                    self.api.llm.send_llm_text_streamed_signal(
                        LLMResponse(
                            message="✅ Model loaded and ready for chat\n",
                            is_end_of_message=False,
                        )
                    )
                except Exception:
                    self.emit_signal(
                        SignalCode.LLM_TEXT_STREAMED_SIGNAL,
                        {
                            "response": LLMResponse(
                                message="✅ Model loaded and ready for chat\n",
                                is_end_of_message=False,
                            )
                        },
                    )

                if getattr(self, "_pending_conversation_message", None):
                    self.logger.info(
                        "Processing pending conversation load after workflow manager became available."
                    )
                    self.load_conversation(self._pending_conversation_message)
                    self._pending_conversation_message = None
                return

        if not self._chat_model:
            self.logger.error("ChatModel failed to load")
        if not self._workflow_manager:
            self.logger.error("Workflow manager failed to load")
        if needs_model_and_tokenizer:
            if not self._model:
                self.logger.error("Model failed to load")
            if not self._tokenizer and not self._is_mistral3_model():
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
        """Handle an incoming request for LLM generation."""
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
        self._interrupted = True
        self.logger.info("Interrupt requested - will stop generation")

        if self._chat_model and hasattr(self._chat_model, "set_interrupted"):
            self._chat_model.set_interrupted(True)

    def on_conversation_deleted(self, data: Dict) -> None:
        """Handle conversation deletion event."""
        if self._workflow_manager:
            self._workflow_manager.clear_memory()

    def clear_history(self, data: Optional[Dict] = None) -> None:
        """Clear chat history and set up a new conversation."""
        data = data or {}
        conversation = self._get_or_create_conversation(data)

        if conversation:
            Conversation.make_current(conversation.id)
            self.logger.info(
                f"Starting new conversation with ID: {conversation.id}"
            )

        if self._workflow_manager:
            if conversation:
                self._workflow_manager.set_conversation_id(conversation.id)
            else:
                self._workflow_manager.clear_memory()

    def _get_or_create_conversation(
        self, data: Dict
    ) -> Optional[Conversation]:
        """Get existing conversation or create a new one."""
        conversation_id = data.get("conversation_id")

        if not conversation_id:
            # No conversation_id provided - create a new one
            conversation = Conversation.create()
            if conversation:
                data["conversation_id"] = conversation.id
                self.update_llm_generator_settings(
                    current_conversation_id=conversation.id
                )
                return conversation
            return None

        # Conversation ID provided - load and set it as current
        conversation = Conversation.objects.get(conversation_id)
        if conversation:
            self.update_llm_generator_settings(
                current_conversation_id=conversation_id
            )
        return conversation

    def add_chatbot_response_to_history(self, message: str) -> None:
        """Add a chatbot-generated response to the chat history."""
        pass

    def load_conversation(self, message: Dict) -> None:
        """Load an existing conversation into the chat workflow."""
        conversation_id = message.get("conversation_id")

        if self._workflow_manager is not None:
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
            self._pending_conversation_message = None
        else:
            self.logger.warning(
                f"Workflow manager not loaded. Will use ConversationHistoryManager for conversation ID: {conversation_id}."
            )
            self._pending_conversation_message = message

    def reload_rag_engine(self) -> None:
        """Reload the Retrieval-Augmented Generation engine."""
        if self._tool_manager:
            self._unload_tool_manager()
            self._load_tool_manager()
            if self._workflow_manager:
                self._workflow_manager.update_tools(self.tools)
        else:
            self.logger.warning("Cannot reload RAG - tool manager not loaded")

    def on_section_changed(self) -> None:
        """Handle section change events."""
        pass

    def _load_tokenizer(self) -> None:
        """Load the tokenizer for the selected model."""
        if self._tokenizer is not None:
            return

        try:
            config = AutoConfig.from_pretrained(
                self.model_path,
                local_files_only=AIRUNNER_LOCAL_FILES_ONLY,
                trust_remote_code=True,
            )

            is_mistral3 = (
                hasattr(config, "model_type")
                and config.model_type == "mistral3"
            ) or (
                hasattr(config, "architectures")
                and any(
                    "Mistral3" in arch for arch in (config.architectures or [])
                )
            )

            if is_mistral3:
                self.logger.info(
                    "Detected Mistral3 model - tokenizer will be handled by chat adapter using mistral_common"
                )
                # Mistral3 models use Tekken tokenizer which is NOT HuggingFace compatible
                # The model directory has tekken.json, which requires mistral_common package
                tekken_path = os.path.join(self.model_path, "tekken.json")
                if not os.path.exists(tekken_path):
                    raise FileNotFoundError(
                        f"tekken.json not found at {tekken_path}. "
                        f"Ensure the model is fully downloaded."
                    )

                self.logger.info(
                    f"✓ Found tekken.json at {tekken_path} - will use mistral_common for tokenization"
                )
                # The chat adapter (chat_huggingface_local.py) will initialize
                # MistralTokenizer when needed for function calling
                return
            else:
                # Standard tokenizer loading for other models
                try:
                    self._tokenizer = AutoTokenizer.from_pretrained(
                        self.model_path,
                        local_files_only=AIRUNNER_LOCAL_FILES_ONLY,
                        trust_remote_code=False,
                    )
                except (KeyError, Exception) as e:
                    self.logger.warning(
                        f"Failed to load tokenizer with trust_remote_code=False: {type(e).__name__}"
                    )
                    self.logger.info("Retrying with trust_remote_code=True")
                    try:
                        self._tokenizer = AutoTokenizer.from_pretrained(
                            self.model_path,
                            local_files_only=AIRUNNER_LOCAL_FILES_ONLY,
                            trust_remote_code=True,
                        )
                    except KeyError as ke:
                        self.logger.warning(
                            f"Tokenizer class not in TOKENIZER_MAPPING: {type(ke).__name__}"
                        )
                        self.logger.info(
                            "Trying with use_fast=False to use slow tokenizer"
                        )
                        self._tokenizer = AutoTokenizer.from_pretrained(
                            self.model_path,
                            local_files_only=AIRUNNER_LOCAL_FILES_ONLY,
                            trust_remote_code=True,
                            use_fast=False,
                        )

            if self._tokenizer:
                self._tokenizer.use_default_system_prompt = False
        except Exception as e:
            self.logger.error(
                f"Error loading tokenizer: {type(e).__name__}: {str(e)}"
            )
            self.logger.error(
                f"Tokenizer traceback:\n{traceback.format_exc()}"
            )
            self._tokenizer = None
            self.logger.error("Tokenizer failed to load")

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

    def _select_dtype(self) -> str:
        """Select and configure quantization dtype."""
        dtype = self.llm_dtype
        self.logger.info(f"Current dtype setting: {dtype}")

        if not dtype or dtype == "auto":
            dtype = self._auto_select_quantization()
            self.llm_generator_settings.dtype = dtype
            self.logger.info(f"✓ Auto-selected quantization: {dtype}")
        else:
            self.logger.info(f"Using configured dtype: {dtype}")

        return dtype

    def _create_bitsandbytes_config(
        self, dtype: str
    ) -> Optional[BitsAndBytesConfig]:
        """Create BitsAndBytes quantization configuration."""
        if dtype not in ["8bit", "4bit", "2bit"]:
            self.logger.info(
                f"Loading full precision model (no quantization) - dtype={dtype}"
            )
            return None

        self.logger.info(f"Using BitsAndBytes runtime {dtype} quantization")

        if dtype == "8bit":
            config = BitsAndBytesConfig(
                load_in_8bit=True,
                llm_int8_threshold=6.0,
                llm_int8_has_fp16_weight=False,
                llm_int8_enable_fp32_cpu_offload=True,
            )
            self.logger.info(
                "Created 8-bit BitsAndBytes config with CPU offload"
            )
            return config

        if dtype in ["4bit", "2bit"]:
            if dtype == "2bit":
                self.logger.warning(
                    "2-bit quantization requires GPTQ/AWQ with calibration dataset"
                )
                self.logger.warning("Falling back to 4-bit BitsAndBytes")

            config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_compute_dtype=torch.float16,
                bnb_4bit_use_double_quant=True,
                bnb_4bit_quant_type="nf4",
            )
            self.logger.info("Created 4-bit BitsAndBytes config")
            return config

        return None

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

    def _configure_quantization_memory(self, dtype: str) -> Dict[str, Any]:
        """Configure memory limits for quantization."""
        if not torch.cuda.is_available():
            self.logger.info(f"✓ Applying {dtype} quantization (no CUDA)")
            self.logger.info(
                f"  Using device_map='auto', dtype={self.torch_dtype}"
            )
            return {}

        if dtype == "8bit":
            self.logger.info("✓ Applying 8-bit quantization with CPU offload")
            self.logger.info(
                f"  Using device_map='auto', dtype={self.torch_dtype}, max_memory=13GB GPU + 18GB CPU"
            )
            return {0: "13GB", "cpu": "18GB"}

        if dtype == "4bit":
            self.logger.info("✓ Applying 4-bit quantization (GPU-only)")
            self.logger.info(
                f"  Using device_map='auto', dtype={self.torch_dtype}, max_memory=14GB GPU (reserves 1.5GB for activations)"
            )
            return {0: "14GB"}

        self.logger.info(f"✓ Applying {dtype} quantization")
        self.logger.info(
            f"  Using device_map='auto', dtype={self.torch_dtype}"
        )
        return {}

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
            self._load_model_from_pretrained(
                model_path, is_mistral3, model_kwargs
            )
            self._load_adapters()

        except Exception as e:
            self.logger.error(
                f"Error loading model: {type(e).__name__}: {str(e)}"
            )
            self.logger.error(f"Model traceback:\n{traceback.format_exc()}")
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
        except Exception as e:
            self.logger.error(f"Error creating ChatModel: {e}", exc_info=True)
            self._chat_model = None

    def _load_tool_manager(self) -> None:
        """Load the tool manager."""
        if self._tool_manager is not None:
            return

        try:
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
        except AttributeError as e:
            self.logger.warning(f"Error unloading model: {e}")
            self._model = None

    def _unload_tokenizer(self) -> None:
        """Unload the tokenizer from memory."""
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
        """Generate a response using the loaded LLM."""
        if self._current_model_path != self.model_path:
            self.unload()
            self.load()

        llm_request = llm_request or LLMRequest()

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

        complete_response = ""
        sequence_counter = 0
        self._interrupted = False

        if not self._workflow_manager:
            self.logger.error("Workflow manager is not initialized")
            return {"response": "Error: workflow unavailable"}

        def handle_streaming_token(token_text: str) -> None:
            """Forward streaming tokens to the GUI and accumulate response."""
            nonlocal complete_response, sequence_counter

            if not token_text:
                return
            complete_response += token_text
            sequence_counter += 1
            self.api.llm.send_llm_text_streamed_signal(
                LLMResponse(
                    node_id=llm_request.node_id if llm_request else None,
                    message=token_text,
                    is_end_of_message=False,
                    is_first_message=(sequence_counter == 1),
                    sequence_number=sequence_counter,
                )
            )

        self._workflow_manager.set_token_callback(handle_streaming_token)

        try:
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                torch.cuda.synchronize()

            result = self._workflow_manager.invoke(prompt)

            if self._interrupted:
                self.logger.info("Generation interrupted by user")
                interrupt_msg = "\n\n[Generation interrupted]"
                complete_response += interrupt_msg
                self.api.llm.send_llm_text_streamed_signal(
                    LLMResponse(
                        node_id=llm_request.node_id if llm_request else None,
                        message=interrupt_msg,
                        is_end_of_message=True,
                        sequence_number=sequence_counter + 1,
                    )
                )
                result = {"messages": []}
        except Exception as exc:
            self.logger.error(f"Error during generation: {exc}", exc_info=True)
            error_message = f"Error: {exc}"
            complete_response = error_message
            self.api.llm.send_llm_text_streamed_signal(
                LLMResponse(
                    node_id=llm_request.node_id if llm_request else None,
                    message=error_message,
                    is_end_of_message=False,
                )
            )
            result = {"messages": []}
        finally:
            self._workflow_manager.set_token_callback(None)
            self._interrupted = False

        if result and "messages" in result:
            final_messages = [
                message
                for message in result["messages"]
                if isinstance(message, AIMessage)
            ]
            if final_messages:
                final_content = final_messages[-1].content or ""
                if final_content:
                    complete_response = final_content

        sequence_counter += 1
        self.api.llm.send_llm_text_streamed_signal(
            LLMResponse(
                node_id=llm_request.node_id if llm_request else None,
                is_end_of_message=True,
                sequence_number=sequence_counter,
            )
        )

        return {"response": complete_response}

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
