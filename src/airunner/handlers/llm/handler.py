import random
import os
import torch
from typing import Optional, Dict, List
from peft import PeftModel

from transformers.utils.quantization_config import BitsAndBytesConfig, GPTQConfig
from transformers import AutoModelForCausalLM, AutoTokenizer
from transformers.generation.streamers import TextIteratorStreamer

from llama_index.llms.groq import Groq
from llama_index.core.chat_engine.types import AgentChatResponse

from airunner.handlers.base_handler import BaseHandler
from airunner.enums import SignalCode, ModelType, ModelStatus, LLMActionType
from airunner.settings import MAX_SEED
from airunner.utils.clear_memory import clear_memory
from airunner.handlers.llm.agent.mistral_agent import MistralAgentQObject
from airunner.handlers.llm.training_mixin import TrainingMixin
from airunner.handlers.llm.llm_request import LLMRequest


class LLMHandler(
    BaseHandler,
    TrainingMixin
):
    model_type: ModelType = ModelType.LLM
    model_class: str = "llm"
    _model: Optional[object] = None
    _streamer: Optional[object] = None
    _chat_engine: Optional[object] = None
    _chat_agent: Optional[MistralAgentQObject] = None
    _llm_with_tools: Optional[object] = None
    _agent_executor: Optional[object] = None
    _embed_model: Optional[object] = None
    _service_context_model: Optional[object] = None
    _use_query_engine: bool = False
    _use_chat_engine: bool = True
    _user_evaluation: str = ""
    _restrict_tools_to_additional: bool = True
    _return_agent_code: bool = False
    _rag_tokenizer: Optional[object] = None
    _rag_retriever: Optional[object] = None
    _vocoder: Optional[object] = None
    _tokenizer: Optional[object] = None
    _generator: Optional[object] = None
    _history: Optional[List] = []
    _current_model_path: Optional[str] = None

    @property
    def is_mistral(self) -> bool:
        path = self._current_model_path.lower()
        return "ministral" in path

    @property
    def is_llama_instruct(self):
        path = self._current_model_path.lower()
        if "instruct" in path and "llama" in path:
            return True
        return False

    @property
    def username(self):
        return self.user.username

    @property
    def botname(self):
        if self.chatbot.assign_names:
            return self.chatbot.botname
        return "Assistant"

    @property
    def _quantization_config(self):
        config = None
        if self.llm_dtype == "8bit":
            config = BitsAndBytesConfig(
                load_in_4bit=False,
                load_in_8bit=True,
                llm_int8_threshold=6.0,
                llm_int8_has_fp16_weight=False,
                bnb_4bit_compute_dtype=torch.bfloat16,
                bnb_4bit_use_double_quant=True,
                bnb_4bit_quant_type='nf4',
            )
        elif self.llm_dtype == "4bit":
            config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_compute_dtype=torch.float16  # changed to match input type
            )
        elif self.llm_dtype == "2bit":
            config = GPTQConfig(
                bits=2,
                dataset="c4",
                tokenizer=self._tokenizer
            )
        return config

    @property
    def use_cache(self):
        if self.llm_generator_settings.override_parameters:
            return self.llm_generator_settings.use_cache
        return self.chatbot.use_cache

    @property
    def model_version(self) -> str:
        model_version = self.chatbot.model_version
        if self.llm_generator_settings.override_parameters:
            model_version = self.llm_generator_settings.model_version
        return model_version

    @property
    def model_path(self):
        return os.path.expanduser(os.path.join(
            self.path_settings.base_path,
            "text",
            "models",
            "llm",
            "causallm",
            self.model_version
        ))
    
    def load(self):
        if self.model_status in (
            ModelStatus.LOADING,
            ModelStatus.LOADED
        ):
            return
        self.unload()
        self.change_model_status(ModelType.LLM, ModelStatus.LOADING)
        self._current_model_path = self.model_path
        self._load_tokenizer()
        self._load_model()
        self._load_streamer()
        self._load_agent()
        if self._model and self._tokenizer and self._streamer and self._chat_agent:
            self.change_model_status(ModelType.LLM, ModelStatus.LOADED)
        else:
            self.change_model_status(ModelType.LLM, ModelStatus.FAILED)

    def unload(self):
        if self.model_status in (
            ModelStatus.LOADING,
            ModelStatus.UNLOADED
        ):
            return
        self.logger.debug("Unloading LLM")
        self.change_model_status(ModelType.LLM, ModelStatus.LOADING)
        self._unload_streamer()
        self._unload_llm_with_tools()
        self._unload_agent_executor()
        self._unload_embed_model()
        self._unload_model()
        self._unload_tokenizer()
        self._unload_agent()
        clear_memory()
        self.change_model_status(ModelType.LLM, ModelStatus.UNLOADED)

    def handle_request(self, data: Dict) -> AgentChatResponse:
        self.logger.debug("Handling request")
        self._do_set_seed()
        self.load()
        action = self.llm_generator_settings.action
        if type(action) is str:
            action = LLMActionType[action]
        return self._do_generate(
            prompt=data["request_data"]["prompt"],
            action=action,
            llm_request=data.get("llm_request_data", None),
        )

    # def chat(
    #     self,
    #     prompt: str,
    #     system_prompt: Optional[str] = None,
    #     rag_system_prompt: Optional[str] = None
    # ) -> AgentChatResponse:
    #     return self._do_generate(
    #         prompt=prompt,
    #         action=LLMActionType.CHAT,
    #         system_prompt=system_prompt,
    #         rag_system_prompt=rag_system_prompt
    #     )

    def do_interrupt(self):
        """
        Public method to interrupt the chat process
        """
        if self._chat_agent:
            self._chat_agent.interrupt_process()

    def clear_history(self, data: Optional[Dict] = None):
        """
        Public method to clear the chat agent history
        """
        if not self._chat_agent:
            return
        self.logger.debug("Clearing chat history")
        self._chat_agent.clear_history(data)

    def add_chatbot_response_to_history(self, message):
        """
        Public method to add a chatbot response to the chat agent history
        """
        self._chat_agent.add_chatbot_response_to_history(message)

    def load_conversation(self, message):
        """
        Public method to load a conversation into the chat agent
        """
        self._chat_agent.on_load_conversation(message)

    def reload_rag(self):
        """
        Public method to reload the RAG model
        """
        self._chat_agent.reload_rag_engine()

    def _load_tokenizer(self):
        if self._tokenizer is not None:
            return
        self.logger.debug(f"Loading tokenizer from {self.model_path}")
        try:
            self._tokenizer = AutoTokenizer.from_pretrained(
                self.model_path,
                local_files_only=True,
                device_map=self.device,
                trust_remote_code=False,
                torch_dtype=self.torch_dtype,
                attn_implementation="flash_attention_2",
            )
            self.logger.debug("Tokenizer loaded")
        except Exception as e:
            self.logger.error(e)

        if self._tokenizer:
            self._tokenizer.use_default_system_prompt = False
        else:
            self.logger.error("Tokenizer failed to load")

    def _load_model(self):
        if self._model is not None:
            return
        self.logger.debug("transformer_base_handler.load_model Loading model")
        if self.llm_generator_settings.use_api:
            self._model = Groq(
                model=self.llm_generator_settings.api_model,
                api_key=self.llm_generator_settings.api_key,
            )
        else:
            self._load_model_local()

    def _load_streamer(self):
        if self._streamer is not None:
            return
        self.logger.debug("Loading LLM text streamer")
        self._streamer = TextIteratorStreamer(self._tokenizer)

    def _load_agent(self):
        if self._chat_agent is not None:
            return
        self.logger.debug("Loading agent")
        # def get_weather(
        #     location: str = Field(
        #         description="The location to get the weather for.",
        #     )
        # ) -> str:
        #     """Get the weather report for a given location."""
        #     return f"{location} is sunny today."

        tools = [
            # FunctionTool.from_defaults(
            #     get_weather,
            #     return_direct=True
            # ),
        ]
        self._chat_agent = MistralAgentQObject(
            model=self._model,
            tokenizer=self._tokenizer,
            default_tool_choice=None
        )

    def _unload_streamer(self):
        self.logger.debug("Unloading streamer")
        try:
            del self._streamer
        except AttributeError as e:
            self.logger.warning(f"Error unloading streamer: {e}")
        self._streamer = None

    def _unload_llm_with_tools(self):
        self.logger.debug("Unloading LLM with tools")
        try:
            del self._llm_with_tools
        except AttributeError as e:
            self.logger.warning(f"Error unloading LLM with tools: {e}")
        self._llm_with_tools = None

    def _unload_agent_executor(self):
        self.logger.debug("Unloading agent executor")
        try:
            del self._agent_executor
        except AttributeError as e:
            self.logger.warning(f"Error unloading agent executor: {e}")
        self._agent_executor = None

    def _unload_embed_model(self):
        self.logger.debug("Unloading embed model")
        try:
            del self._embed_model
        except AttributeError as e:
            self.logger.warning(f"Error unloading embed model: {e}")
        self._embed_model = None

    def _unload_model(self):
        self.logger.debug("Unloading model")
        self._model = None
        return True

    def _unload_tokenizer(self):
        self.logger.debug("Unloading tokenizer")
        try:
            del self._tokenizer
        except AttributeError as e:
            self.logger.warning(f"Error unloading tokenizer {e}")
        self._tokenizer = None
        clear_memory(self.memory_settings.default_gpu_llm)
        return True

    def _unload_agent(self):
        self.logger.debug("Unloading agent")
        do_clear_memory = False
        if self._chat_agent is not None:
            self.logger.debug("Unloading chat agent")
            self._chat_agent.unload()
            try:
                del self._chat_agent
            except AttributeError as e:
                self.logger.warning(f"Error unloading chat agent: {e}")
            self._chat_agent = None
            do_clear_memory = True
        return do_clear_memory

    def _load_model_local(self):
        self.logger.debug(f"Loading local LLM model from {self.model_path}")
        try:
            # Use the same path as tokenizer
            self._model = AutoModelForCausalLM.from_pretrained(
                self.model_path,
                local_files_only = True,
                use_cache = self.use_cache,
                trust_remote_code = False,
                torch_dtype = self.torch_dtype,
                device_map = self.device,
            )
        except Exception as e:
            self.logger.error(f"Error loading model: {e}")
            return
        
        try:
            if os.path.exists(self.adapter_path):
                # Convert base model to PEFT format
                self._model = PeftModel.from_pretrained(self._model, self.adapter_path)
        except Exception as e:
            self.logger.error(f"Error loading adapter (continuing with base model): {e}")
        
    def _do_generate(
        self, 
        prompt: str, 
        action: LLMActionType,
        system_prompt: Optional[str] = None,
        rag_system_prompt: Optional[str] = None,
        llm_request: Optional[LLMRequest] = None
    ) -> AgentChatResponse:
        self.logger.debug("Generating response")
        if self._current_model_path != self.model_path:
            self.unload()
            self.load()
        # if action is LLMActionType.CHAT and self.chatbot.use_mood:
        #     action = LLMActionType.UPDATE_MOOD
        response = self._chat_agent.chat(
            message=prompt, 
            action=action, 
            system_prompt=system_prompt, 
            rag_system_prompt=rag_system_prompt,
            llm_request=llm_request
        )
        if action is LLMActionType.CHAT:
            self._send_final_message()
        return response

    def _emit_streamed_text_signal(self, **kwargs):
        self.logger.debug("Emitting streamed text signal")
        kwargs["name"] = self.botname
        self.emit_signal(
            SignalCode.LLM_TEXT_STREAMED_SIGNAL,
            kwargs
        )

    def _send_final_message(self):
        self.logger.debug("Sending final message")
        self._emit_streamed_text_signal(
            message="",
            is_first_message=False,
            is_end_of_message=True
        )

    def _do_set_seed(self):
        self.logger.debug("Setting seed")

        if self.llm_generator_settings.override_parameters:
            seed = self.llm_generator_settings.seed
            random_seed = self.llm_generator_settings.random_seed
        else:
            seed = self.chatbot.seed
            random_seed = self.chatbot.random_seed

        if random_seed:
            seed = random.randint(-MAX_SEED, MAX_SEED)

        torch.manual_seed(seed)
        torch.cuda.manual_seed(seed)
        torch.cuda.manual_seed_all(seed)
        random.seed(seed)
        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark = False
        if self._tokenizer:
            self._tokenizer.seed = seed
