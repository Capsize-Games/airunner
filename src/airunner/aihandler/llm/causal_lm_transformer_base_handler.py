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

    def __init__(self, agent_class: BaseAgent, do_load_on_init: bool = False, *args, **kwargs):
        self.agent_class_ = agent_class if agent_class is not None else BaseAgent
        self.agent_options = kwargs.pop("agent_options", {})
        self.streamer = None
        self.chat_engine = None
        self.chat_agent = None
        self.llm_with_tools = None
        self.agent_executor = None
        self.embed_model = None
        self.service_context_model = None
        self.use_query_engine: bool = False
        self.use_chat_engine: bool = True
        self._username: str = ""
        self._botname: str = ""
        self.bot_mood: str = ""
        self.bot_personality: str = ""
        self.user_evaluation: str = ""
        self.tools: dict = self.load_tools()
        self.action: LLMActionType = LLMActionType.CHAT
        self.use_personality: bool = False
        self.use_mood: bool = False
        self.use_guardrails: bool = False
        self.use_system_instructions: bool = False
        self.assign_names: bool = False
        self.prompt_template: str = ""
        self.guardrails_prompt: str = ""
        self.system_instructions: str = ""
        self.restrict_tools_to_additional: bool = True
        self.return_agent_code: bool = False
        self.batch_size: int = 1
        self.model_type = ModelType.LLM
        self.rag_tokenizer = None
        self.rag_retriever = None
        self.do_quantize_model = kwargs.pop("do_quantize_model", True)
        self.callback = None
        self.request_data = kwargs.get("request_data", {})
        self.__model = None
        self.vocoder = None
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
        self.model_path = kwargs.get("model_path", None)
        self.current_model_path = kwargs.get("current_model_path", "")
        self.use_cache = kwargs.get("use_cache", True)
        self.history = []
        self.sequences = kwargs.get("sequences", 1)
        self.seed = kwargs.get("seed", 42)
        self.set_attention_mask = kwargs.get("set_attention_mask", False)
        self.do_push_to_hub = kwargs.get("do_push_to_hub", False)
        self.llm_int8_enable_fp32_cpu_offload = kwargs.get("llm_int8_enable_fp32_cpu_offload", True)
        self.generator_name = kwargs.get("generator_name", "")
        self.default_model_path = kwargs.get("default_model_path", "")
        self.return_result = kwargs.get("return_result", True)
        self.skip_special_tokens = kwargs.get("skip_special_tokens", True)
        self.do_sample = kwargs.get("do_sample", True)
        self._processing_request = kwargs.get("_processing_request", False)
        self.bad_words_ids = kwargs.get("bad_words_ids", None)
        self.bos_token_id = kwargs.get("bos_token_id", None)
        self.pad_token_id = kwargs.get("pad_token_id", None)
        self.eos_token_id = kwargs.get("eos_token_id", None)
        self.no_repeat_ngram_size = kwargs.get("no_repeat_ngram_size", 1)
        self.decoder_start_token_id = kwargs.get("decoder_start_token_id", None)
        self.tokenizer = None
        self._generator = None
        self.template = None
        self.image = None
        self.model_class = "llm"

        super().__init__(*args, **kwargs)

        if self.model_path is None:
            self.model_path = self.get_model_path(self.chatbot.model_version)

        if do_load_on_init:
            self.load()

        self.register(SignalCode.LLM_TOKENIZER_LOAD_SIGNAL, self.on_load_tokenizer_signal)
        self.register(SignalCode.LLM_TOKENIZER_UNLOAD_SIGNAL, self.on_unload_tokenizer_signal)

    @property
    def is_mistral(self) -> bool:
        path = self.model_path.lower()
        return "mistral" in path

    @property
    def is_llama_instruct(self):
        path = self.model_path.lower()
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
        if self.assign_names:
            return self._username
        return "User"

    @property
    def botname(self):
        if self.assign_names:
            return self._botname
        return "Assistant"

    @property
    def model(self):
        return self.__model

    @model.setter
    def model(self, value):
        if value is None and self.__model is not None:
            self.__model.quantization_method = None
            self.__model.to("cpu")
            del self.__model
            self.__model = None
            clear_memory(self.memory_settings.default_gpu_llm)
        self.__model = value

    @property
    def do_load_model(self):
        if self.model is None or self.current_model_path != self.model_path:
            return True
        return False

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

    def on_load_tokenizer_signal(self):
        self.load_tokenizer()

    def on_unload_tokenizer_signal(self):
        self._unload_tokenizer()

    def on_load_model_signal(self):
        self.load()

    def on_interrupt_process_signal(self):
        if self.chat_agent is not None:
            self.chat_agent.interrupt_process()

    def on_clear_history_signal(self):
        if self.chat_agent is not None:
            self.logger.debug("Clearing chat history")
            self.chat_agent.clear_history()

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

    def process_data(self, data):
        self.logger.debug("Processing data")
        self.request_data = data.get("request_data", {})
        self.callback = self.request_data.get("callback", None)
        self.use_gpu = self.request_data.get("use_gpu", self.use_gpu)
        self.image = self.request_data.get("image", None)
        self.model_path = self.request_data.get("model_path", self.model_path)
        self.template = self.request_data.get("template", "")
        self._username = self.chatbot.username
        self._botname = self.chatbot.botname
        self.bot_mood = self.chatbot.bot_mood
        self.bot_personality = self.chatbot.bot_personality
        self.use_personality = self.chatbot.use_personality
        self.use_mood = self.chatbot.use_mood
        self.use_guardrails = self.chatbot.use_guardrails
        self.use_system_instructions = self.chatbot.use_system_instructions
        self.assign_names = self.chatbot.assign_names
        self.prompt_template = self.chatbot.prompt_template
        self.guardrails_prompt = self.chatbot.guardrails_prompt
        self.system_instructions = self.chatbot.system_instructions
        self.batch_size = self.llm_generator_settings.batch_size
        action = self.llm_generator_settings.action
        for action_type in LLMActionType:
            if action_type.value == action:
                self.action = action_type
                break

    def move_to_device(self, device=None):
        if not self.model:
            return
        if device:
            device_name = device
        elif self.llm_dtype in ["2bit", "4bit", "8bit", "16bit"] and self.use_cuda:
            device_name = "cuda"
        else:
            device_name = "cpu"
        self.logger.debug("Moving model to device {device_name}")
        self.model.to(device_name)

    def pre_load(self):
        """
        This function is called at the start of the load function.
        Override this function to add custom preload functionality.
        :return:
        """
        self.current_model_path = self.model_path

    def load(self):
        if self.model_status in (
            ModelStatus.LOADED,
            ModelStatus.LOADING
        ):
            return
        self.logger.debug("Loading model from transformer_base_handler.load")
        do_load_model = self.do_load_model
        do_load_tokenizer = self.tokenizer is None

        if any((do_load_model, do_load_tokenizer)):
            self.pre_load()

            if do_load_tokenizer:
                self.load_tokenizer()

            if do_load_model:
                self.load_model()

            self.post_load()

    def post_load(self):
        self.load_tokenizer()

        do_load_streamer = self.streamer is None
        if do_load_streamer:
            self.load_streamer()

        do_load_agent = self.chat_agent is None
        if do_load_agent:
            self.load_agent()

    def load_model(self):
        self.logger.debug("transformer_base_handler.load_model Loading model")
        if self.llm_generator_settings.use_api:
            self.model = Groq(
                model=self.llm_generator_settings.api_model,
                api_key=self.llm_generator_settings.api_key,
            )
            self.model_status = ModelStatus.LOADED
        else:
            self.load_model_local()

    def quantization_config(self):
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

    def model_params(self) -> dict:
        return {
            'local_files_only': True,
            'use_cache': self.use_cache,
            'trust_remote_code': self.application_settings.trust_remote_code
        }

    def get_model_path(self, path:str) -> str:
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

    def load_model_local(self):
        params = self.model_params()
        path = self.get_model_path(self.chatbot.model_version)
        is_quantized = os.path.exists(path)
        if not is_quantized:
            path = self.get_model_path(self.chatbot.model_version)

        self.logger.debug(f"Loading model from {path}")

        if self.do_quantize_model and self.use_cuda:
            config = self.quantization_config()
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

    def save_quantized_model(self):
        self.logger.debug("Saving quantized model to cache")
        model_path = self.get_model_path(self.chatbot.model_version)
        self.model.save_pretrained(model_path)

    def load_tokenizer(self):
        if self.tokenizer is not None:
            return

        path = self.get_model_path(self.chatbot.model_version)

        self.logger.debug(f"Loading tokenizer from {path}")
        kwargs = {
            "local_files_only": True,
            "token": self.request_data.get("hf_api_key_read_key"),
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

    def load_agent(self):
        self.logger.debug("Loading agent")
        self.chat_agent = self.agent_class_(
            model=self.model,
            tokenizer=self.tokenizer,
            streamer=self.streamer,
            tools=self.tools,
            chat_template=self.chat_template,
            is_mistral=self.is_mistral,
        )

    def unload_agent(self):
        self.logger.debug("Unloading agent")
        do_clear_memory = False
        if self.chat_agent is not None:
            self.logger.debug("Unloading chat agent")
            self.chat_agent.unload()
            del self.chat_agent
            self.chat_agent = None
            do_clear_memory = True
        return do_clear_memory

    def load_streamer(self):
        self.logger.debug("Loading LLM text streamer")
        self.streamer = TextIteratorStreamer(self.tokenizer)

    def unload(self):
        self.logger.debug("Unloading LLM")
        self.unload_streamer()
        self.unload_llm_with_tools()
        self.unload_agent_executor()
        self.unload_embed_model()
        self.unload_agent()
        if self.model_status is ModelStatus.LOADING:
            self._requested_action = ModelAction.CLEAR
            return False
        elif self.model_status is not ModelStatus.LOADED:
            return False
        self.model_status = ModelStatus.LOADING
        self._processing_request = False
        self._unload_model()
        self._unload_tokenizer()
        self.image = None
        self.model_status = ModelStatus.UNLOADED

    def unload_streamer(self):
        self.logger.debug("Unloading streamer")
        del self.streamer
        self.streamer = None

    def unload_llm_with_tools(self):
        self.logger.debug("Unloading LLM with tools")
        del self.llm_with_tools
        self.llm_with_tools = None

    def unload_agent_executor(self):
        self.logger.debug("Unloading agent executor")
        del self.agent_executor
        self.agent_executor = None

    def unload_embed_model(self):
        self.logger.debug("Unloading embed model")
        del self.embed_model
        self.embed_model = None

    def generate(self, prompt: str, action: LLMActionType):
        return self.do_generate(prompt, action)

    def do_generate(self, prompt: str, action: LLMActionType):
        self.logger.debug("Generating response")
        if action is LLMActionType.CHAT and self.chatbot.use_mood:
            action = LLMActionType.UPDATE_MOOD
        self.chat_agent.run(
            prompt,
            action
        )
        self.send_final_message()

    def emit_streamed_text_signal(self, **kwargs):
        kwargs["name"] = self.botname
        self.emit_signal(
            SignalCode.LLM_TEXT_STREAMED_SIGNAL,
            kwargs
        )

    def send_final_message(self):
        self.emit_streamed_text_signal(
            message="",
            is_first_message=False,
            is_end_of_message=True
        )

    def do_set_seed(self, seed=None):
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

    def handle_request(self, data: dict):
        self.logger.debug("Handling request")
        self._processing_request = True
        self.process_data(data)
        self.do_set_seed(self.chatbot.seed)
        self.load()
        self._processing_request = True
        action = data["request_data"]["action"]
        if type(action) is str:
            action = LLMActionType(action)
        self.generate(
            data["request_data"]["prompt"],
            action
        )
