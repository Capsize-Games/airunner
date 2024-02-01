import asyncio
import random
import traceback

import torch
from transformers import BitsAndBytesConfig, GPTQConfig

from airunner.aihandler.base_handler import BaseHandler
from airunner.utils import clear_memory


class TransformerBaseHandler(BaseHandler):
    auto_class_ = None

    @property
    def do_load_model(self):
        if self.model is None or self.current_model_path != self.model_path:
            return True
        return False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.callback = None
        self.request_data = {}
        self.model = None
        self.processor = None
        self.vocoder = None
        self.temperature = 0.7
        self.max_length = 1000
        self.min_length = 0
        self.num_beams = 1
        self.top_k = 20
        self.eta_cutoff = 10
        self.top_p = 1.0
        self.repetition_penalty = 1.15
        self.early_stopping = True
        self.length_penalty = 1.0
        self.parameters = None
        self.model_path = None
        self.override_parameters = None
        self.prompt = None
        self.do_quantize_model = True
        self.current_model_path = ""
        self.local_files_only = False
        self.use_cache = False
        self.history = []
        self.sequences = 1
        self.seed = 42
        self.set_attention_mask = False
        self.do_push_to_hub = False
        self.llm_int8_enable_fp32_cpu_offload = True
        self.generator_name = ""
        self.default_model_path = ""
        self.request_type = ""
        self.return_result = True
        self.skip_special_tokens = True
        self.do_sample = True
        self._processing_request = False
        self.bad_words_ids = None
        self.bos_token_id = None
        self.pad_token_id = None
        self.eos_token_id = None
        self.no_repeat_ngram_size = 1
        self.decoder_start_token_id = None
        self.tokenizer = None
        self._generator = None
        self.template = None
        self.image = None

    def quantization_config(self):
        config = None
        if self.llm_dtype == "8bit":
            self.logger.info("Loading 8bit model")
            config = BitsAndBytesConfig(
                load_in_4bit=False,
                load_in_8bit=True,
                llm_int8_threshold=200.0,
                llm_int8_has_fp16_weight=False,
                bnb_4bit_compute_dtype=torch.float16,
                bnb_4bit_use_double_quant=True,
                bnb_4bit_quant_type='nf4',
            )
        elif self.llm_dtype == "4bit":
            self.logger.info("Loading 4bit model")
            config = BitsAndBytesConfig(
                load_in_4bit=True,
                load_in_8bit=False,
                llm_int8_threshold=200.0,
                llm_int8_has_fp16_weight=False,
                bnb_4bit_compute_dtype=torch.float16,
                bnb_4bit_use_double_quant=True,
                bnb_4bit_quant_type='nf4',
            )
        elif self.llm_dtype == "2bit":
            self.logger.info("Loading 2bit model")
            config = GPTQConfig(
                bits=2,
                dataset="c4",
                tokenizer=self.tokenizer
            )
        return config

    def model_params(self, local_files_only) -> dict:
        local_files_only = self.local_files_only if local_files_only is None else local_files_only
        return {
            'local_files_only': local_files_only,
            'device_map': self.device,
            'use_cache': self.use_cache,
            'torch_dtype': torch.float16 if self.llm_dtype != "32bit" else torch.float32,
            'trust_remote_code': True
        }

    def load_model(self, local_files_only=None):
        self.logger.info("Loading model")
        params = self.model_params(local_files_only=local_files_only)
        if self.request_data:
            params["token"] = self.request_data.get(
                "hf_api_key_read_key",
                ""
            )

        if self.do_quantize_model:
            config = self.quantization_config()
            if config:
                params["quantization_config"] = config

        self.logger.info(f"Loading model from {self.current_model_path}")
        try:
            self.model = self.auto_class_.from_pretrained(
                self.current_model_path,
                **params
            )
        except OSError as e:
            if "Checkout your internet connection" in str(e):
                if local_files_only:
                    return self.load_model(local_files_only=False)
                else:
                    self.logger.error(e)

        # print the type of class that self.model is

    def load_tokenizer(self, local_files_only=None):
        pass

    def load_processor(self, local_files_only=None):
        pass

    def unload(self):
        self._processing_request = False
        if (
            self.unload_model() or
            self.unload_tokenizer() or
            self.unload_processor()
        ):
            clear_memory()

    def unload_tokenizer(self):
        self.logger.info("Unloading tokenizer")
        if self.tokenizer:
            self.tokenizer = None
            return True

    def unload_model(self):
        if self.model:
            self.model = None
            return True

    def unload_processor(self):
        self.logger.info("Unloading processor")
        if self.processor:
            self.processor = None
            return True

    def pre_load(self):
        """
        This function is called at the start of the load function.
        Override this function to add custom pre load functionality.
        :return:
        """
        self.current_model_path = self.model_path

    def load(self):
        self.logger.info("Loading LLM")
        do_load_model = self.do_load_model
        do_load_tokenizer = self.tokenizer is None
        do_load_processor = self.processor is None

        self.pre_load()

        if do_load_tokenizer:
            self.load_tokenizer()

        if do_load_processor:
            self.load_processor()

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

    def generate(self):
        print("GENERATE")
        return self.do_generate()

    def do_generate(self):
        raise NotImplementedError

    def process_data(self, data):
        self.request_data = data.get("request_data", {})
        self.callback = self.request_data.get("callback", None)
        self.use_gpu = self.request_data.get("use_gpu", self.use_gpu)
        self.image = self.request_data.get("image", None)
        self.parameters = self.request_data.get("parameters", {})
        self.model_path = self.request_data.get("model_path", self.model_path)
        self.override_parameters = self.parameters.get("override_parameters", self.override_parameters)
        self.prompt = self.request_data.get("prompt", self.prompt)
        self.template = self.request_data.get("template", "")

    def move_to_cpu(self):
        if self.model:
            self.logger.info("Moving model to CPU")
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
        self.logger.info("Moving model to device {device_name}")
        self.model.to(device_name)

    def prepare_input_args(self):
        self.logger.info("Preparing input args")
        parameters = self.parameters or {}
        top_k = parameters.get("top_k", self.top_k)
        eta_cutoff = parameters.get("eta_cutoff", self.eta_cutoff)
        top_p = parameters.get("top_p", self.top_p)
        num_beams = parameters.get("num_beams", self.num_beams)
        repetition_penalty = parameters.get("repetition_penalty", self.repetition_penalty)
        early_stopping = parameters.get("early_stopping", self.early_stopping)
        max_length = parameters.get("max_length", self.max_length)
        min_length = parameters.get("min_length", self.min_length)
        temperature = parameters.get("temperature", self.temperature)
        return_result = parameters.get("return_result", self.return_result)
        skip_special_tokens = parameters.get("skip_special_tokens", self.skip_special_tokens)
        do_sample = parameters.get("do_sample", self.do_sample)
        bad_words_ids = parameters.get("bad_words_ids", self.bad_words_ids)
        bos_token_id = parameters.get("bos_token_id", self.bos_token_id)
        pad_token_id = parameters.get("pad_token_id", self.pad_token_id)
        eos_token_id = parameters.get("eos_token_id", self.eos_token_id)
        no_repeat_ngram_size = parameters.get("no_repeat_ngram_size", self.no_repeat_ngram_size)
        sequences = parameters.get("sequences", self.sequences)
        decoder_start_token_id = parameters.get("decoder_start_token_id", self.decoder_start_token_id)
        use_cache = parameters.get("use_cache", self.use_cache)
        seed = parameters.get("seed", self.seed)

        kwargs = {
            "max_length": max_length,
            "min_length": min_length,
            "do_sample": do_sample,
            "early_stopping": early_stopping,
            "num_beams": num_beams,
            "temperature": temperature,
            "top_k": top_k,
            "eta_cutoff": eta_cutoff,
            "top_p": top_p,
            "repetition_penalty": repetition_penalty,
            # "bad_words_ids": bad_words_ids,
            # "bos_token_id": bos_token_id,
            # "pad_token_id": pad_token_id,
            # "eos_token_id": eos_token_id,
            "return_result": return_result,
            "skip_special_tokens": skip_special_tokens,
            "no_repeat_ngram_size": no_repeat_ngram_size,
            "num_return_sequences": sequences,  # if num_beams == 1 or num_beams < sequences else num_beams,
            "decoder_start_token_id": decoder_start_token_id,
            "use_cache": use_cache,
            "seed": seed,
        }
        if "top_k" in kwargs and "do_sample" in kwargs and not kwargs["do_sample"]:
            del kwargs["top_k"]

        return kwargs

    def do_set_seed(self, seed=None):
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

    def handle_request(self, data):
        self.logger.info("Handling generate request")
        self._processing_request = True
        kwargs = self.prepare_input_args()
        self.do_set_seed(kwargs.get("seed"))
        self.process_data(data)
        self.load()
        self._processing_request = True
        return self.generate()
