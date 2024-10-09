import random
import os

import torch

from llama_index.llms.groq import Groq

from transformers.utils.quantization_config import BitsAndBytesConfig, GPTQConfig
from transformers import AutoModelForCausalLM, AutoTokenizer
from transformers.generation.streamers import TextIteratorStreamer

from airunner.handlers.base_handler import BaseHandler
from airunner.enums import SignalCode, ModelType, ModelStatus, LLMActionType
from airunner.settings import MAX_SEED
from airunner.utils.clear_memory import clear_memory
from airunner.handlers.llm.agent.base_agent import BaseAgent


class CausalLMTransformerBaseHandler(
    BaseHandler
):
    auto_class_ = AutoModelForCausalLM
    tokenizer_class_ = AutoTokenizer
    model_type = ModelType.LLM

    def __init__(self, *args, **kwargs):
        self.model_type = ModelType.LLM
        self.model_class = "llm"
        self.agent_options = kwargs.pop("agent_options", {})
        self._model = None
        self._streamer = None
        self._chat_engine = None
        self._chat_agent = None
        self._llm_with_tools = None
        self._agent_executor = None
        self._embed_model = None
        self._service_context_model = None
        self._use_query_engine: bool = False
        self._use_chat_engine: bool = True
        self._user_evaluation: str = ""
        self._restrict_tools_to_additional: bool = True
        self._return_agent_code: bool = False
        self._rag_tokenizer = None
        self._rag_retriever = None
        self._do_quantize_model = kwargs.pop("do_quantize_model", True)
        self.__model = None
        self._vocoder = None
        self._current_model_path = kwargs.get("current_model_path", "")
        self._history = []
        self._set_attention_mask = kwargs.get("set_attention_mask", False)
        self._do_push_to_hub = kwargs.get("do_push_to_hub", False)
        self._llm_int8_enable_fp32_cpu_offload = kwargs.get("llm_int8_enable_fp32_cpu_offload", True)
        self._generator_name = kwargs.get("generator_name", "")
        self._return_result = kwargs.get("return_result", True)
        self._skip_special_tokens = kwargs.get("skip_special_tokens", True)
        self._processing_request = kwargs.get("_processing_request", False)
        self._bad_words_ids = kwargs.get("bad_words_ids", None)
        self._bos_token_id = kwargs.get("bos_token_id", None)
        self._pad_token_id = kwargs.get("pad_token_id", None)
        self._eos_token_id = kwargs.get("eos_token_id", None)
        self._no_repeat_ngram_size = kwargs.get("no_repeat_ngram_size", 1)
        self._decoder_start_token_id = kwargs.get("decoder_start_token_id", None)
        self._tokenizer = None
        self._generator = None

        super().__init__(*args, **kwargs)

    @property
    def is_mistral(self) -> bool:
        path = self._current_model_path.lower()
        return "mistral" in path

    @property
    def is_llama_instruct(self):
        path = self._current_model_path.lower()
        if "instruct" in path and "llama" in path:
            return True
        return False

    @property
    def chat_template(self):
        if self.is_mistral:
            return (
                "{% for message in messages %}"
                "{% if message['role'] == 'system' %}"
                "{{ '[INST] <<SYS>>' + message['content'] + ' <</SYS>>[/INST]' }}"
                "{% elif message['role'] == 'user' %}"
                "{{ '[INST]' + message['content'] + ' [/INST]' }}"
                "{% elif message['role'] == 'assistant' %}"
                "{{ message['content'] + eos_token + ' ' }}"
                "{% endif %}"
                "{% endfor %}"
            )
        elif self.is_llama_instruct:
            return (
                "{{ '<|begin_of_text|>' }}"
                "{% for message in messages %}"
                "{{ '<|start_header_id|>' + "
                "message['role'] + '<|end_header_id|>' + '\n\n' + message['content'] + "
                "'<|end_header_id|>\n\n' + message['content'] + '<|eot_id|>' }}"
                "{% endfor %}"
            )

    @property
    def username(self):
        if self.chatbot.assign_names:
            return self.chatbot.username
        return "User"

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
            config = BitsAndBytesConfig(load_in_4bit=True)
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
    def model_path(self):
        model_version:str = self.chatbot.model_version
        if self.llm_generator_settings.override_parameters:
            model_version = self.llm_generator_settings.model_version
        current_llm_generator = self.application_settings.current_llm_generator
        local_path:str = "misc"
        if current_llm_generator == "causallm":
            local_path = "causallm"
        elif current_llm_generator == "seq2seq":
            local_path = "seq2seq"
        elif current_llm_generator == "visualqa":
            local_path = "visualqa"
        base:str = self.path_settings.base_path
        return os.path.expanduser(os.path.join(
            base,
            "text",
            "models",
            "llm",
            local_path,
            model_version
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

    def handle_request(self, data:dict):
        self.logger.debug("Handling request")
        self._processing_request = True
        self._do_set_seed()
        self.load()
        self._processing_request = True
        action = self.llm_generator_settings.action
        if type(action) is str:
            action = LLMActionType[action]
        self._do_generate(
            data["request_data"]["prompt"],
            action
        )

    def do_interrupt(self):
        """
        Public method to interrupt the chat process
        """
        if self._chat_agent:
            self._chat_agent.interrupt_process()

    def clear_history(self):
        """
        Public method to clear the chat agent history
        """
        self.logger.debug("Clearing chat history")
        self._chat_agent.clear_history()

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
        self._chat_agent.reload_rag()

    def _load_tokenizer(self):
        if self._tokenizer is not None:
            return
        path = self.model_path
        self.logger.debug(f"Loading tokenizer from {path}")
        kwargs = {
            "local_files_only": True,
            "device_map": self.device,
            "trust_remote_code": True,
            "torch_dtype": self.torch_dtype,
            "attn_implementation": "flash_attention_2",
        }

        if self.chat_template:
            kwargs["chat_template"] = self.chat_template
        try:
            self._tokenizer = self.tokenizer_class_.from_pretrained(
                path,
                **kwargs,
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
        self._chat_agent = BaseAgent(
            model=self._model,
            tokenizer=self._tokenizer,
            streamer=self._streamer,
            chat_template=self.chat_template,
            is_mistral=self.is_mistral,
        )

    def _unload_streamer(self):
        self.logger.debug("Unloading streamer")
        del self._streamer
        self._streamer = None

    def _unload_llm_with_tools(self):
        self.logger.debug("Unloading LLM with tools")
        del self._llm_with_tools
        self._llm_with_tools = None

    def _unload_agent_executor(self):
        self.logger.debug("Unloading agent executor")
        del self._agent_executor
        self._agent_executor = None

    def _unload_embed_model(self):
        self.logger.debug("Unloading embed model")
        del self._embed_model
        self._embed_model = None

    def _unload_model(self):
        self.logger.debug("Unloading model")
        self._model = None
        return True

    def _unload_tokenizer(self):
        self.logger.debug("Unloading tokenizer")
        del self._tokenizer
        self._tokenizer = None
        clear_memory(self.memory_settings.default_gpu_llm)
        return True

    def _unload_agent(self):
        self.logger.debug("Unloading agent")
        do_clear_memory = False
        if self._chat_agent is not None:
            self.logger.debug("Unloading chat agent")
            self._chat_agent.unload()
            del self._chat_agent
            self._chat_agent = None
            do_clear_memory = True
        return do_clear_memory

    def _load_model_local(self):
        self.logger.debug("Loading local LLM model")
        path = self.model_path
        is_quantized = os.path.exists(path)
        if not is_quantized:
            path = self.model_path
        params = dict(
            local_files_only=True,
            use_cache=self.use_cache,
            trust_remote_code=False,
            torch_dtype=self.torch_dtype,
            device_map=self.device,
        )
        if self._do_quantize_model and self.use_cuda:
            config = self._quantization_config
            if config:
                params["quantization_config"] = config
        try:
            with torch.no_grad():
                self._model = self.auto_class_.from_pretrained(
                    path,
                    **params
                )
        except Exception as e:
            self.logger.error(f"Error loading model: {e}")
            self._model = None

    def _do_generate(self, prompt: str, action: LLMActionType):
        self.logger.debug("Generating response")
        model_path = self.model_path
        if self._current_model_path != model_path:
            self.unload()
            self.load()
        if action is LLMActionType.CHAT and self.chatbot.use_mood:
            action = LLMActionType.UPDATE_MOOD
        self._chat_agent.run(
            prompt,
            action
        )
        self._send_final_message()

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

    def _save_quantized_model(self):
        self.logger.debug("Saving quantized model to cache")
        self._model.save_pretrained(self.model_path)

    def _clear_memory(self):
        self.logger.debug("Clearing memory")
        clear_memory(self.memory_settings.default_gpu_llm)
