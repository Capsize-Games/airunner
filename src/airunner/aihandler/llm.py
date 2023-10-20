import os
import random
from enum import Enum

from airunner.aihandler.conversation_handler import ConversationManager
from airunner.aihandler.enums import MessageCode

import torch

from PyQt6.QtCore import pyqtSignal, QObject
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer, BitsAndBytesConfig, AutoModelForCausalLM

from airunner.aihandler.logger import Logger
from airunner.data.models import LLMGenerator
from airunner.data.db import session
from airunner.aihandler.logger import Logger as logger


class MessageType(Enum):
    INFO = 0
    WARNING = 1
    ERROR = 2
    SUCCESS = 3
    PROGRESS = 4


class RequestType(Enum):
    STANDARD = 0
    FUNCTION = 1


class LLM(QObject):
    _current_model_path = None
    running = False
    message_signal = pyqtSignal(int, str)
    _generator = None
    _current_generator_name = None
    _requested_generator_name = None
    _processing_request = False
    callback = None
    _model = None
    _tokenizer = None
    use_cache = False
    local_files_only = False
    llm_int8_enable_fp32_cpu_offload = True
    use_gpu = True
    dtype = ""
    do_push_to_hub = False

    @property
    def device_map(self):
        return "cpu" if not self.has_gpu else "auto"

    @property
    def current_model_path(self):
        return self._current_model_path

    @property
    def has_gpu(self):
        if self.dtype == "32bit" or not self.use_gpu:
            return False
        return torch.cuda.is_available()

    def __init__(self, *args, **kwargs):
        self.engine = kwargs.pop("engine", None)
        super().__init__(*args, **kwargs)
        self.prompt_generator = ConversationManager(llm=self)

    @property
    def model(self):
        if not self._model:
            try:
                self.load_model()
            except torch.cuda.OutOfMemoryError:
                print("Out of memory")
                self.load_model()
            except Exception as e:
                print(e)
        return self._model

    @model.setter
    def model(self, value):
        self._model = value

    @property
    def tokenizer(self):
        if not self._tokenizer:
            try:
                self.load_tokenizer()
            except torch.cuda.OutOfMemoryError:
                print("Out of memory")
                self.load_tokenizer()
        return self._tokenizer

    @property
    def generator(self):
        if not self._generator or self._current_generator_name != self._requested_generator_name:
            self._current_generator_name = self._requested_generator_name
            self._generator = session.query(LLMGenerator).filter_by(name=self._current_generator_name).first()
        return self._generator

    def move_to_cpu(self):
        if self.model:
            self.model.to("cpu")
        self._tokenizer = None

    def move_to_device(self, device=None):
        if not self.model:
            return
        if device:
            self.model.to(device)
            return
        if self.dtype in ["4bit", "8bit", "16bit"] and self.has_gpu:
            self.model.to("cuda")
        else:
            self.model.to("cpu")

    def unload_model(self):
        logger.info("Unload model")
        self._model = None

    def unload_tokenizer(self):
        logger.info("Unload tokenizer")
        self._tokenizer = None

    def initialize_model(self, generator_name, model_path):
        logger.info("Initialize model")
        self._requested_generator_name = generator_name
        if self._requested_generator_name != generator_name or model_path != self.current_model_path:
            self.unload_model()
            self.unload_tokenizer()
            self._current_model_path = model_path

    def is_valid_property(self, property):
        return property in self.model.config.to_dict()

    def is_float_property(self, property):
        return isinstance(self.model.config.to_dict()[property], float)

    def process_input(self, prompt):
        logger.info("Process input")
        inputs = self.tokenizer(prompt, return_tensors="pt").to("cuda" if self.has_gpu else "cpu")
        return inputs

    def load_model(self, local_files_only = None):
        local_files_only = self.local_files_only if local_files_only is None else local_files_only

        quantization_config = None

        if self.dtype == "8bit":
            logger.info("Loading 8bit model")
            quantization_config = BitsAndBytesConfig(
                load_in_8bit=True,
                bnb_8bit_use_double_quant=True,
                llm_int8_enable_fp32_cpu_offload=True,
                llm_int8_threshold=6.0,
            )
        elif self.dtype == "4bit":
            logger.info("Loading 4bit model")
            quantization_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_use_double_quant=True,
                llm_int8_enable_fp32_cpu_offload=True,
                llm_int8_threshold=6.0,
            )
        elif self.dtype == "16bit":
            logger.info("Loading 16bit model")
        else:
            logger.info("Loading 32bit model")

        params = {
            "local_files_only": self.local_files_only,
            "device_map": self.device_map,
            "use_cache": self.use_cache,
        }

        if quantization_config:
            params["quantization_config"] = quantization_config

        if self.dtype == "16bit":
            params["torch_dtype"] = torch.float16
        elif self.dtype == "32bit":
            params["torch_dtype"] = torch.float32

        #path = f"/home/joe/.airunner/llm/models/{self.current_model_path}"
        # if not os.path.exists(path):
        #     path = self.current_model_path
        path = self.current_model_path
        logger.info(f"Loading {self.generator.name} model from {path}")
        try:
            if self.generator.name == "Flan":
                self.model = AutoModelForSeq2SeqLM.from_pretrained(
                    path,
                    **params
                )
        except OSError as e:
            if self.local_files_only:
                self.load_model(local_files_only=local_files_only)
            else:
                raise e

        if self.do_push_to_hub:
            self.push_to_hub()

        self._model.eval()

    def push_to_hub(self):
        path = f"{self.engine.hf_username}/{self.current_model_path.split('/')[1]}"
        self.model.push_to_hub(path, token=self.engine.hf_api_key_write_key)
        self.tokenizer.push_to_hub(path, token=self.engine.hf_api_key_write_key)

    def load_tokenizer(self):
        logger.info("Load tokenizer")
        self._tokenizer = AutoTokenizer.from_pretrained(
            self.current_model_path,
            local_files_only=self.local_files_only,
        )

    def disable_request_processing(self):
        self._processing_request = True

    def enable_request_processing(self):
        self._processing_request = True

    def do_generate(self, data):
        logger.info("Do generate")
        self.dtype = data["request_data"]["dtype"]
        self.use_gpu = data["request_data"]["use_gpu"]
        generator_name = data["request_data"]["generator_name"]
        model_path = data["request_data"]["model_path"]


        Logger.info(f"Generating with {generator_name} at {model_path}")
        self.disable_request_processing()

        # initialize the model
        self.initialize_model(generator_name, model_path)

        # get the prompt based on request_type and input
        value = self.prompt_generator.generate(data)

        self.engine.send_message(value, code=MessageCode.TEXT_GENERATED)
        self.enable_request_processing()

    seed = 42

    def do_set_seed(self, seed=None):
        from transformers import set_seed as _set_seed
        seed = self.seed if seed is None else seed
        self.seed = seed
        _set_seed(self.seed)
        # set model and token seed
        torch.manual_seed(self.seed)
        torch.cuda.manual_seed(self.seed)
        torch.cuda.manual_seed_all(self.seed)
        random.seed(self.seed)
        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark = False
        if self.tokenizer:
            self.tokenizer.seed = self.seed
        if self.model:
            self.model.seed = self.seed

    def generate(self, **kwargs):
        # parse properties
        properties = self.parse_properties(kwargs)

        self.do_set_seed(properties.get("seed"))

        # process the input
        prompt = kwargs.pop("prompt")
        inputs = self.process_input(prompt)

        # generate the output
        logger.info("Generating text...")
        for k, v in properties.items():
            if k == "top_k" and "do_sample" in properties and not properties["do_sample"]:
                continue
            inputs[k] = v
        outputs = self.model.generate(**inputs)

        # decode the output
        value = self.tokenizer.batch_decode(
            outputs,
            skip_special_tokens=kwargs.get("skip_special_tokens", True)
        )[0]

        return value

    def parse_properties(self, properties: dict):
        return {
            "max_length": properties.get("max_length", 20),
            "min_length": properties.get("min_length", 0),
            "do_sample": properties.get("do_sample", True),
            "early_stopping": properties.get("early_stopping", True),
            "num_beams": properties.get("num_beams", 1),
            "temperature": properties.get("temperature", 1.0),
            "top_k": properties.get("top_k", 1),
            "top_p": properties.get("top_p", 0.9),
            "repetition_penalty": properties.get("repetition_penalty", 50.0),
            "bad_words_ids": properties.get("bad_words_ids", None),
            "bos_token_id": properties.get("bos_token_id", None),
            "pad_token_id": properties.get("pad_token_id", None),
            "eos_token_id": properties.get("eos_token_id", None),
            "length_penalty": properties.get("length_penalty", 1.0),
            "no_repeat_ngram_size": properties.get("no_repeat_ngram_size", 1),
            "num_return_sequences": properties.get("num_return_sequences", 1),
            "attention_mask": properties.get("attention_mask", None),
            "decoder_start_token_id": properties.get("decoder_start_token_id", None),
            "use_cache": properties.get("use_cache", None),
        }

    def process_setting(self, name, val):
        if type(val) == int:
            if name in ["top_p", "ngram_size"]:
                return val / 100
            elif name == "repetition_penalty":
                return val / 10000
            elif name in ["length_penalty", "temperature"]:
                return val / 100
        return val