import os
import random
import torch
from transformers.utils.quantization_config import BitsAndBytesConfig, GPTQConfig
from airunner.aihandler.base_handler import BaseHandler
from airunner.enums import SignalCode, ModelType, ModelStatus, LLMActionType
from airunner.utils.clear_memory import clear_memory
from airunner.utils.get_torch_device import get_torch_device


class TransformerBaseHandler(BaseHandler):
    auto_class_ = None

    def __init__(self, *args, do_load_on_init: bool = False, **kwargs):
        self.do_quantize_model = kwargs.pop("do_quantize_model", True)

        super().__init__(*args, **kwargs)
        self.callback = None
        self.request_data = kwargs.get("request_data", {})
        self.model = None
        self.vocoder = None
        self.temperature = kwargs.get("temperature", 0.7)
        #self.max_length = kwargs.get("max_length", 1000)
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
        self.override_parameters = {}
        self.model_type = "llm"

        if self.model_path is None:
            self.model_path = self.settings["llm_generator_settings"]["model_version"]

        if do_load_on_init:
            self.load()

        self.register(SignalCode.LLM_UNLOAD_MODEL_SIGNAL, self.on_unload_model_signal)

    def on_unload_model_signal(self, message: dict):
        self.unload_model()

    @property
    def do_load_model(self):
        if self.model is None or self.current_model_path != self.model_path:
            return True
        return False

    @property
    def cache_llm_to_disk(self):
        return self.settings["llm_generator_settings"]["cache_llm_to_disk"]

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
                #llm_int8_enable_fp32_cpu_offload=True,
            )
        elif self.llm_dtype == "4bit":
            config = BitsAndBytesConfig(
                load_in_4bit=True,
                load_in_8bit=False,
                llm_int8_threshold=6.0,
                llm_int8_has_fp16_weight=False,
                bnb_4bit_compute_dtype=torch.bfloat16,
                bnb_4bit_use_double_quant=True,
                bnb_4bit_quant_type='nf4',
                # llm_int8_enable_fp32_cpu_offload=True,
            )
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
            'trust_remote_code': self.settings["trust_remote_code"]
        }

    def get_model_standard_path(self, path) -> str:
        current_llm_generator = self.settings.get("current_llm_generator", "")
        if current_llm_generator == "causallm":
            local_path = self.settings["path_settings"]["llm_causallm_model_path"]
        elif current_llm_generator == "seq2seq":
            local_path = self.settings["path_settings"]["llm_seq2seq_model_path"]
        elif current_llm_generator == "visualqa":
            local_path = self.settings["path_settings"]["llm_visualqa_model_path"]
        else:
            local_path = self.settings["path_settings"]["llm_misc_model_path"]
        local_path = os.path.join(local_path, path)
        return os.path.expanduser(local_path)

    def get_model_cache_path(self, path) -> str:
        model_name = path.split("/")[-1]
        current_llm_generator = self.settings.get("current_llm_generator", "")
        if current_llm_generator == "causallm":
            local_path = self.settings["path_settings"]["llm_causallm_model_cache_path"]
        elif current_llm_generator == "seq2seq":
            local_path = self.settings["path_settings"]["llm_seq2seq_model_cache_path"]
        elif current_llm_generator == "visualqa":
            local_path = self.settings["path_settings"]["llm_visualqa_model_cache_path"]
        else:
            local_path = self.settings["path_settings"]["llm_misc_model_cache_path"]
        local_path = os.path.join(local_path, self.llm_dtype, model_name)
        return os.path.expanduser(local_path)

    def get_model_path(self, path):
        if self.do_quantize_model:
            local_path = self.get_model_cache_path(path)
            if self.cache_llm_to_disk and os.path.exists(local_path):
                return local_path
            else:
                local_path = self.get_model_standard_path(path)
                if os.path.exists(local_path):
                    return local_path
        return path

    def load_model(self):
        params = self.model_params()

        path = self.get_model_path(self.current_model_path)

        self.logger.debug(f"Loading model from {path}")

        if self.do_quantize_model and self.use_cuda:
            config = self.quantization_config()
            if config:
                params["quantization_config"] = config
            params["torch_dtype"] = torch.bfloat16
            params["device_map"] = self.device
        else:
            params["torch_dtype"] = torch.bfloat16
            params["device_map"] = self.device

        try:
            self.change_model_status(ModelType.LLM, ModelStatus.LOADING, path)
            self.model = self.auto_class_.from_pretrained(
                path,
                **params
            )
            self.change_model_status(ModelType.LLM, ModelStatus.LOADED, path)
        except Exception as e:
            self.change_model_status(ModelType.LLM, ModelStatus.FAILED, path)
            self.logger.error(f"Error loading model: {e}")
            self.model = None

    def save_quantized_model(self):
        if self.do_quantize_model and self.cache_llm_to_disk:
            self.logger.debug("Saving quantized model to cache")
            cache_path = self.get_model_cache_path(self.current_model_path)
            if self.model and self.cache_llm_to_disk and not os.path.exists(cache_path):
                self.model.save_pretrained(cache_path)

    def load_tokenizer(self):
        pass

    def unload(self, do_clear_memory: bool = False):
        self._processing_request = False
        model_unloaded = self.unload_model()
        tokenizer_unloaded = self.unload_tokenizer()
        self.image = None
        if (
            do_clear_memory or
            model_unloaded or
            tokenizer_unloaded
        ):
            self.logger.debug("Clearing memory")
            clear_memory()

    def unload_tokenizer(self):
        self.logger.debug("Unloading tokenizer")
        self.tokenizer = None
        self.change_model_status(ModelType.LLM_TOKENIZER, ModelStatus.UNLOADED, "")
        return True

    def unload_model(self):
        self.logger.debug("Unloading model")
        self.model = None
        self.change_model_status(ModelType.LLM, ModelStatus.UNLOADED, "")
        return True

    def pre_load(self):
        """
        This function is called at the start of the load function.
        Override this function to add custom pre load functionality.
        :return:
        """
        self.current_model_path = self.model_path

    def load(self):
        self.logger.debug("Loading model")
        do_load_model = self.do_load_model
        do_load_tokenizer = self.tokenizer is None

        self.pre_load()

        if do_load_tokenizer:
            self.load_tokenizer()

        if do_load_model:
            self.load_model()

        self.post_load()

    def post_load(self):
        """
        This function is called at the end of the load function.
        Override this function to add custom post load functionality.
        :return:
        """
        self.logger.error("Define post_load here")

    def generate(self, prompt, action) -> str:
        return self.do_generate(prompt, action)

    def do_generate(self, prompt, action) -> str:
        raise NotImplementedError

    @property
    def parameters(self):
        current_chatbot_name = self.settings["llm_generator_settings"]["current_chatbot"]
        settings = self.settings["llm_generator_settings"]["saved_chatbots"][current_chatbot_name]["generator_settings"]
        return settings

    def process_data(self, data: dict) -> None:
        self.logger.debug("Processing data")
        self.request_data = data.get("request_data", {})

        # current_chatbot_name = self.settings["llm_generator_settings"]["current_chatbot"]
        # settings = self.settings["llm_generator_settings"]["saved_chatbots"][current_chatbot_name]["generator_settings"]
        # self.parameters = self.request_data.get("parameters", settings)
        self.callback = self.request_data.get("callback", None)
        self.use_gpu = self.request_data.get("use_gpu", self.use_gpu)
        self.image = self.request_data.get("image", None)
        self.model_path = self.request_data.get("model_path", self.model_path)
        self.template = self.request_data.get("template", "")

    def move_to_cpu(self):
        if self.model:
            self.logger.debug("Moving model to CPU")
            self.model.to("cpu")
        self.tokenizer = None

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

    def do_set_seed(self, seed=None):
        self.logger.debug("Setting seed")
        seed = self.seed if seed is None else seed
        self.seed = seed
        # _set_seed(self.seed)
        # set model and token seed
        torch.manual_seed(self.seed)
        torch.cuda.manual_seed(self.seed)
        torch.cuda.manual_seed_all(self.seed)
        random.seed(self.seed)
        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark = False
        if self.tokenizer:
            self.tokenizer.seed = self.seed

    def handle_request(self, data: dict) -> str:
        self.logger.debug("Handling request")
        self._processing_request = True
        self.process_data(data)
        self.do_set_seed(self.parameters.get("seed", None))
        self.load()
        self._processing_request = True
        action = data["request_data"]["action"]
        if type(action) is str:
            action = LLMActionType(action)
        result = self.generate(
            data["request_data"]["prompt"],
            action
        )
        return result
