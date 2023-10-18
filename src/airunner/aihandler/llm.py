from enum import Enum
from airunner.aihandler.enums import MessageCode

import torch

from PyQt6.QtCore import pyqtSignal, QObject
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

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
    current_model_path = None
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
    load_in_8bit = True
    local_files_only = False
    llm_int8_enable_fp32_cpu_offload = True
    device_map = "auto"
    use_gpu = True

    def __init__(self, *args, **kwargs):
        self.engine = kwargs.pop("engine", None)
        super().__init__(*args, **kwargs)

    @property
    def model(self):
        if not self._model:
            try:
                self.load_model()
            except torch.cuda.OutOfMemoryError:
                print("Out of memory")
                self.load_model()
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
        self.model.to("cpu")
        self.tokenizer.to("cpu")

    def move_to_device(self):
        self.model.to(self.device_map)
        self.tokenizer.to(self.device_map)

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
            self.current_model_path = model_path

    def is_valid_property(self, property):
        return property in self.model.config.to_dict()

    def is_float_property(self, property):
        return isinstance(self.model.config.to_dict()[property], float)

    def process_input(self, prompt):
        logger.info("Process input")
        inputs = self.tokenizer(prompt, return_tensors="pt")
        inputs = inputs.to(self.model.device)

        # get all generator settings, store the properties as key value inside of inputs
        setting = self.generator.generator_settings
        for k in setting.__dict__.keys():
            if self.is_valid_property(k):
                inputs[k] = getattr(setting, k)

        if "do_sample" in inputs.keys() and not inputs["do_sample"] and "top_k" in inputs.keys():
            del inputs["top_k"]

        return inputs

    def load_model(self, local_files_only = None):
        logger.info("Load model")
        local_files_only = self.local_files_only if local_files_only is None else local_files_only
        try:
            self.model = AutoModelForSeq2SeqLM.from_pretrained(
                self.current_model_path,
                torch_dtype=torch.float16 if self.load_in_8bit or self.use_gpu else torch.float32,
                local_files_only=self.local_files_only,
                device_map=self.device_map,
                load_in_8bit=self.load_in_8bit,
                llm_int8_enable_fp32_cpu_offload=self.llm_int8_enable_fp32_cpu_offload,
                use_cache=self.use_cache,
            )
        except OSError as e:
            if self.local_files_only:
                self.load_model(local_files_only=local_files_only)
            else:
                raise e
        self._model.eval()

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
        generator_name, model_path, prompt = data["request_data"]
        
        Logger.info(f"Generating with {generator_name} at {model_path}")
        self.disable_request_processing()

        # initialize the model
        self.initialize_model(generator_name, model_path)

        # process the input
        inputs = self.process_input(prompt)

        # generate the output
        logger.info("Generating text...")
        outputs = self.model.generate(**inputs)

        # decode the output
        value = self.tokenizer.batch_decode(outputs, skip_special_tokens=True)[0]

        # emit the message signal
        self.engine.send_message(value, code=MessageCode.TEXT_GENERATED)

        self.enable_request_processing()

    def process_setting(self, name, val):
        if type(val) == int:
            if name in ["top_p", "ngram_size"]:
                return val / 100
            elif name == "repetition_penalty":
                return val / 10000
            elif name in ["length_penalty", "temperature"]:
                return val / 100
        return val
