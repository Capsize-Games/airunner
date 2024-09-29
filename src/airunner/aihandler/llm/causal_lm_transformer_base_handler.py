import random
import os

import torch

from llama_index.llms.groq import Groq

from transformers.utils.quantization_config import BitsAndBytesConfig, GPTQConfig
from transformers import AutoModelForCausalLM, AutoTokenizer
from transformers.generation.streamers import TextIteratorStreamer

from airunner.aihandler.base_handler import BaseHandler
from airunner.enums import SignalCode, ModelType, ModelStatus, LLMActionType, ModelAction
from airunner.utils.clear_memory import clear_memory
from airunner.aihandler.llm.agent.base_agent import BaseAgent


class CausalLMTransformerBaseHandler(
    BaseHandler
):
    auto_class_ = AutoModelForCausalLM
    tokenizer_class_ = AutoTokenizer
    model_type = ModelType.LLM

    def __init__(self, do_load_on_init: bool = False, *args, **kwargs):
        self.model_type = "llm"
        self.model_class = "llm"
        self.agent_options = kwargs.pop("agent_options", {})
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
        self._tools: dict = self.load_tools()
        self._restrict_tools_to_additional: bool = True
        self._return_agent_code: bool = False
        self._rag_tokenizer = None
        self._rag_retriever = None
        self._do_quantize_model = kwargs.pop("do_quantize_model", True)
        self.__model = None
        self._vocoder = None

        self.temperature = kwargs.get("temperature", 0.7)
        self.max_new_tokens = 30
        self.min_length = kwargs.get("min_length", 0)
        self.num_beams = kwargs.get("num_beams", 1)
        self.top_k = kwargs.get("top_k", 20)
        self.eta_cutoff = kwargs.get("eta_cutoff", 10)
        self.top_p = kwargs.get("top_p", 1.0)
        self.repetition_penalty = kwargs.get("repetition_penalty", 1.15)
        self.early_stopping = kwargs.get("early_stopping", True)
        self.length_penalty = kwargs.get("length_penalty", 1.0)
        self.sequences = kwargs.get("sequences", 1)
        self.seed = kwargs.get("seed", 42)
        self.do_sample = kwargs.get("do_sample", True)

        self._current_model_path = kwargs.get("current_model_path", "")
        self._history = []
        self._set_attention_mask = kwargs.get("set_attention_mask", False)
        self._do_push_to_hub = kwargs.get("do_push_to_hub", False)
        self._llm_int8_enable_fp32_cpu_offload = kwargs.get("llm_int8_enable_fp32_cpu_offload", True)
        self._generator_name = kwargs.get("generator_name", "")
        self._default_model_path = kwargs.get("default_model_path", "")
        self._return_result = kwargs.get("return_result", True)
        self._skip_special_tokens = kwargs.get("skip_special_tokens", True)
        self._processing_request = kwargs.get("_processing_request", False)
        self._bad_words_ids = kwargs.get("bad_words_ids", None)
        self._bos_token_id = kwargs.get("bos_token_id", None)
        self._pad_token_id = kwargs.get("pad_token_id", None)
        self._eos_token_id = kwargs.get("eos_token_id", None)
        self._no_repeat_ngram_size = kwargs.get("no_repeat_ngram_size", 1)
        self._decoder_start_token_id = kwargs.get("decoder_start_token_id", None)
        self.tokenizer = None
        self._generator = None

        super().__init__(*args, **kwargs)

        if do_load_on_init:
            self.load()

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
    def model(self):
        return self.__model

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
                tokenizer=self.tokenizer
            )
        return config

    @property
    def use_cache(self):
        if self.llm_generator_settings.override_parameters:
            return self.llm_generator_settings.use_cache
        else:
            return self.chatbot.use_cache

    @model.setter
    def model(self, value):
        if value is None and self.__model is not None:
            del self.__model
            self.__model = None
            clear_memory(self.memory_settings.default_gpu_llm)
        self.__model = value

    @staticmethod
    def load_tools() -> dict:
        return {
            # LLMToolName.QUIT_APPLICATION.value: QuitApplicationTool(),
            # LLMToolName.STT_START_CAPTURE.value: StartAudioCaptureTool(),
            # LLMToolName.STT_STOP_CAPTURE.value: StopAudioCaptureTool(),
            # LLMToolName.TTS_ENABLE.value: StartSpeakersTool(),
            # LLMToolName.TTS_DISABLE.value: StopSpeakersTool(),
            # LLMToolName.LLM_PROCESS_STT_AUDIO.value: ProcessAudioTool(),
            # LLMToolName.BASH_EXECUTE.value: BashExecuteTool(),
            # LLMToolName.WRITE_FILE.value: WriteFileTool(),
        }

    def load_llm(self):
        self._load_tokenizer()
        self._load_model()
        self._load_streamer()
        self._load_agent()

    def unload_llm(self):
        self.logger.debug("Unloading LLM")
        self._unload_streamer()
        self._unload_llm_with_tools()
        self._unload_agent_executor()
        self._unload_embed_model()
        self._unload_model()
        self._unload_tokenizer()
        self._unload_agent()
        self.model_status = ModelStatus.UNLOADED

    def handle_request(self, data:dict):
        self.logger.debug("Handling request")
        self._processing_request = True
        self._do_set_seed(self.chatbot.seed)
        self.load()
        self._processing_request = True
        action = self.llm_generator_settings.action
        if type(action) is str:
            action = LLMActionType(action)
        self._do_generate(
            data["request_data"]["prompt"],
            action
        )

    def do_interrupt(self):
        """
        Public method to interrupt the chat process
        """
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

    def reload_rag(self, data):
        """
        Public method to reload the RAG model
        """
        self._chat_agent.reload_rag(data)

    def _load_tokenizer(self):
        if self.tokenizer is not None:
            return

        path = self._get_model_path(self.chatbot.model_version)

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
            self.tokenizer = self.tokenizer_class_.from_pretrained(
                path,
                **kwargs,
            )
            self.logger.debug("Tokenizer loaded")
        except Exception as e:
            self.logger.error(e)
            self.model_status = ModelStatus.FAILED

        if self.tokenizer:
            self.tokenizer.use_default_system_prompt = False
        else:
            self.logger.error("Tokenizer failed to load")

    def _load_model(self):
        if self.model is not None:
            return
        self.logger.debug("transformer_base_handler.load_model Loading model")
        if self.llm_generator_settings.use_api:
            self.model = Groq(
                model=self.llm_generator_settings.api_model,
                api_key=self.llm_generator_settings.api_key,
            )
            self.model_status = ModelStatus.LOADED
        else:
            self._load_model_local()

    def _load_streamer(self):
        if self._streamer is not None:
            return
        self.logger.debug("Loading LLM text streamer")
        self._streamer = TextIteratorStreamer(self.tokenizer)

    def _load_agent(self):
        if self._chat_agent is not None:
            return
        self.logger.debug("Loading agent")
        self._chat_agent = BaseAgent(
            model=self.model,
            tokenizer=self.tokenizer,
            streamer=self._streamer,
            tools=self._tools,
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
        self.model = None
        return True

    def _unload_tokenizer(self):
        self.logger.debug("Unloading tokenizer")
        del self.tokenizer
        self.tokenizer = None
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

    def _get_model_path(self, path:str) -> str:
        current_llm_generator = self.application_settings.current_llm_generator
        if current_llm_generator == "causallm":
            local_path = "causallm"
        elif current_llm_generator == "seq2seq":
            local_path = "seq2seq"
        elif current_llm_generator == "visualqa":
            local_path = "visualqa"
        else:
            local_path = "misc"
        return os.path.expanduser(os.path.join(
            self.path_settings.base_path,
            "text/models",
            local_path,
            path
        ))

    def _load_model_local(self):
        params = dict(
            local_files_only=True,
            use_cache=self.use_cache,
            trust_remote_code=False
        )
        path = self._get_model_path(self.chatbot.model_version)
        is_quantized = os.path.exists(path)
        if not is_quantized:
            path = self._get_model_path(self.chatbot.model_version)
        self.logger.debug(f"Loading model from {path}")
        if self._do_quantize_model and self.use_cuda:
            config = self._quantization_config
            if config:
                params["quantization_config"] = config
        params["torch_dtype"] = torch.bfloat16
        params["device_map"] = self.device
        try:
            self.model_status = ModelStatus.LOADING
            with torch.no_grad():
                self.model = self.auto_class_.from_pretrained(
                    path,
                    **params
                )
            self.model_status = ModelStatus.LOADED
        except Exception as e:
            self.model_status = ModelStatus.FAILED
            self.logger.error(f"Error loading model: {e}")
            self.model = None

    def _do_generate(self, prompt: str, action: LLMActionType):
        model_path = self._get_model_path(self.chatbot.model_version)
        if self._current_model_path != model_path:
            self._current_model_path = model_path
            self.unload_llm()
            self.load_llm()
        self.logger.debug("Generating response")
        if action is LLMActionType.CHAT and self.chatbot.use_mood:
            action = LLMActionType.UPDATE_MOOD
        self._chat_agent.run(
            prompt,
            action
        )
        self._send_final_message()

    def _emit_streamed_text_signal(self, **kwargs):
        kwargs["name"] = self.botname
        self.emit_signal(
            SignalCode.LLM_TEXT_STREAMED_SIGNAL,
            kwargs
        )

    def _send_final_message(self):
        self._emit_streamed_text_signal(
            message="",
            is_first_message=False,
            is_end_of_message=True
        )

    def _do_set_seed(self, seed=None):
        self.logger.debug("Setting seed")
        seed = self.seed if seed is None else seed
        self.seed = seed
        torch.manual_seed(self.seed)
        torch.cuda.manual_seed(self.seed)
        torch.cuda.manual_seed_all(self.seed)
        random.seed(self.seed)
        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark = False
        if self.tokenizer:
            self.tokenizer.seed = self.seed

    def _save_quantized_model(self):
        self.logger.debug("Saving quantized model to cache")
        model_path = self._get_model_path(self.chatbot.model_version)
        self.model.save_pretrained(model_path)
