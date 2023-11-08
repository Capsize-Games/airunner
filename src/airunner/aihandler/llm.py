import os
import random
from enum import Enum
import re

from airunner.aihandler.enums import MessageCode

import torch

from PyQt6.QtCore import pyqtSignal, QObject
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer, AutoModelForCausalLM
from optimum.gptq import GPTQQuantizer
from transformers import BitsAndBytesConfig
from airunner.aihandler.settings_manager import SettingsManager
from airunner.chat.models import BaseConversationController


from airunner.data.models import LLMGenerator
from airunner.data.db import session
from airunner.aihandler.logger import Logger as logger

import random

from langchain.chains import ConversationChain
from langchain.prompts import PromptTemplate
from langchain.memory import ConversationBufferWindowMemory
from langchain.llms import HuggingFacePipeline


import transformers


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
    set_attention_mask = False
    seed = 42
    default_properties = {
        "max_length": 20,
        "min_length": 0,
        "num_beams": 1,
        "temperature": 1.0,
        "top_k": 1,
        "top_p": 0.9,
        "repetition_penalty": 1.0,
        "length_penalty": 1.0,
        "no_repeat_ngram_size": 1,
        "num_return_sequences": 1,
    }
    properties: dict = default_properties.copy()
    _conversation_controller = None
    
    @property
    def conversation_controller(self):
        if not self._conversation_controller:
            self._conversation_controller = BaseConversationController()
        return self._conversation_controller

    @property
    def do_load_model(self):
        if self.model is None:
            return True
        return False
    
    @property
    def do_load_tokenizer(self):
        if self.tokenizer is None:
            return True
        return False

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

    @property
    def model(self):
        return self._model

    @model.setter
    def model(self, value):
        self._model = value

    @property
    def tokenizer(self):
        return self._tokenizer
    
    @tokenizer.setter
    def tokenizer(self, value):
        self._tokenizer = value

    @property
    def generator(self):
        if not self._generator or self._current_generator_name != self._requested_generator_name:
            self._current_generator_name = self._requested_generator_name
            self._generator = session.query(LLMGenerator).filter_by(name=self._current_generator_name).first()
        return self._generator

    def __init__(self, *args, **kwargs):
        self.engine = kwargs.pop("engine", None)
        super().__init__(*args, **kwargs)
        self.settings_manager = SettingsManager()
        self.prompt_template_path = "aihandler/chat_templates/conversation.j2"

    def move_to_cpu(self):
        if self.model:
            logger.info("Moving model to CPU")
            self.model.to("cpu")
        self._tokenizer = None

    def move_to_device(self, device=None):
        if not self.model:
            return
        if device:
            device_name = device
        elif self.dtype in ["2bit", "4bit", "8bit", "16bit"] and self.has_gpu:
            device_name = "cuda"
        else:
            device_name = "cpu"
        logger.info("Moving model to device {device_name}")
        self.model.to(device_name)

    def unload_model(self):
        logger.info("Unloading model")
        self._model = None

    def unload_tokenizer(self):
        logger.info("Unloading tokenizer")
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

    def do_build_as_chat(self, request_type):
        # if request_type in ["image_subject_generator", "image_caption_generator"]:
        #     return True
        return False

    def process_input(self, user_input, request_type=""):
        logger.info("Process input")
        prompt = user_input
        messages = prompt

        encodes = self.tokenizer(messages, return_tensors="pt")
        self.set_attention_mask = False
        
        device_name = "cuda" if self.has_gpu else "cpu"
        logger.info(f"Moving inputs to {device_name}")
        inputs = encodes.to(device_name)
        return inputs

    def load_model(self, local_files_only = None):
        if not self.do_load_model:
            return

        local_files_only = self.local_files_only if local_files_only is None else local_files_only

        config = None

        if self.dtype == "8bit":
            logger.info("Loading 8bit model")
            config = BitsAndBytesConfig(
                load_in_4bit=False,
                load_in_8bit=True,
                llm_int8_threshold=200.0,
                llm_int8_has_fp16_weight=False,
                bnb_4bit_compute_dtype=torch.float16,
                bnb_4bit_use_double_quant=True,
                bnb_4bit_quant_type='nf4',
            )
        elif self.dtype == "4bit":
            logger.info("Loading 4bit model")
            config = BitsAndBytesConfig(
                load_in_4bit=True,
                load_in_8bit=False,
                llm_int8_threshold=200.0,
                llm_int8_has_fp16_weight=False,
                bnb_4bit_compute_dtype=torch.float16,
                bnb_4bit_use_double_quant=True,
                bnb_4bit_quant_type='nf4',
            )
        elif self.dtype == "16bit":
            logger.info("Loading 16bit model")
        else:
            logger.info("Loading 32bit model")
        

        params = {
            "local_files_only": self.local_files_only,
            "device_map": self.device_map,
            "use_cache": self.use_cache,
            "torch_dtype": torch.float16 if self.dtype != "32bit" else torch.float32,
            "token": self.settings_manager.hf_api_key_read_key,
        }
        
        if config:
            params["quantization_config"] = config
        path = self.current_model_path
        logger.info(f"Loading {self.generator.name} model from {path}")
        if self.generator.name == "seq2seq":
            self.model = AutoModelForSeq2SeqLM.from_pretrained(
                path,
                **params
            )
        elif self.generator.name == "casuallm":
            self.model = AutoModelForCausalLM.from_pretrained(
                path,
                **params
            )
        
        self.pipeline=transformers.pipeline(
            "text-generation",
            model=self.model,
            tokenizer=self.tokenizer,
            torch_dtype=torch.float16 if self.dtype != "32bit" else torch.float32,
            trust_remote_code=True,
            device_map="auto",
            max_length=1000,
            do_sample=True,
            top_k=10,
            num_return_sequences=1,
            eos_token_id=self.tokenizer.eos_token_id
            )
        self.llm=HuggingFacePipeline(pipeline=self.pipeline, model_kwargs={'temperature':0.7})
        self.memory = ConversationBufferWindowMemory(k=5)
        path = os.path.join(self.prompt_template_path)
        with open(path, "r") as f:
            prompt_template = f.read()
        self.prompt = PromptTemplate.from_template(
            prompt_template, 
            template_format="jinja2", 
            partial_variables={
                "username": self.username,
                "botname": self.botname,
            })
        self.chain = ConversationChain(llm=self.llm, prompt=self.prompt, memory=self.memory)
            
        if self.model:
            if self.do_push_to_hub:
                self.push_to_hub()

    def quantize_model(self, local_files_only = None):
        local_files_only = self.local_files_only if local_files_only is None else local_files_only

        params = {
            "local_files_only": self.local_files_only,
            "device_map": self.device_map,
            "use_cache": self.use_cache,
            "torch_dtype": torch.float16 if self.dtype != "32bit" else torch.float32,
        }
        path = self.current_model_path
        logger.info(f"Loading {self.generator.name} model from {path}")
        try:
            try:
                bits = {
                    "2bit": 2,
                    "4bit": 4,
                    "8bit": 8,
                    "16bit": 16,
                    "32bit": 32,
                }
                self.model = AutoModelForSeq2SeqLM.from_pretrained(
                    path,
                    **params
                )
                quantizer = GPTQQuantizer(bits=bits[self.dtype], dataset=f"c4", block_name_to_quantize = "model.decoder.layers", model_seqlen = 2048)
                self.model = quantizer.quantize_model(self.model, self.tokenizer)
            except torch.cuda.OutOfMemoryError:
                logger.warning("Cuda out of memory, trying to clear cache and loading again")
                self.engine.unload_stablediffusion()
                self.model = AutoModelForSeq2SeqLM.from_pretrained(
                    path,
                    **params
                )
                quantizer = GPTQQuantizer(bits=bits[self.dtype], dataset=f"c4", block_name_to_quantize = "model.decoder.layers", model_seqlen = 2048)
                self.model = quantizer.quantize_model(self.model, self.tokenizer)
            except Exception as e:
                logger.error(e)
        except OSError as e:
            if self.local_files_only:
                self.load_model(local_files_only=local_files_only)
            else:
                raise e
            
        if self.model:
            if self.do_push_to_hub:
                self.push_to_hub()
            self.model.eval()

    def push_to_hub(self):
        path = f"{self.engine.hf_username}/{self.current_model_path.split('/')[1]}"
        self.model.push_to_hub(path, token=self.settings_manager.hf_api_key_write_key)
        self.tokenizer.push_to_hub(path, token=self.settings_manager.hf_api_key_write_key)

    def load_tokenizer(self):
        if not self.do_load_tokenizer:
            return
        logger.info("Load tokenizer")
        self.tokenizer = AutoTokenizer.from_pretrained(
            self.current_model_path,
            local_files_only=self.local_files_only,
            token=self.settings_manager.hf_api_key_read_key,
            device_map=self.device_map,
        )
        self.tokenizer.use_default_system_prompt = False

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


        logger.info(f"Generating with {generator_name} at {model_path}")
        self.disable_request_processing()

        # initialize the model
        self.initialize_model(generator_name, model_path)

        # get the prompt based on request_type and input
        kwargs = {
            **self.properties.copy(),
            "top_k": 20,
            "top_p": 1.0,
            "num_beams": 1,
            "repetition_penalty": 100.0,
            "early_stopping": True,
            "max_length": 200,
            "min_length": 0,
            "temperature": 1.0,
            "return_result": True,
            "skip_special_tokens": True
        }
        parameters = data["request_data"]["parameters"]
        if parameters["override_parameters"]:
            kwargs["top_p"] = parameters["top_p"] / 100.0
            kwargs["max_length"] = parameters["max_length"]
            kwargs["repetition_penalty"] = parameters["repetition_penalty"] / 100.0
            kwargs["min_length"] = parameters["min_length"]
            kwargs["length_penalty"] = parameters["length_penalty"]
            kwargs["num_beams"] = parameters["num_beams"]
            kwargs["ngram_size"] = parameters["ngram_size"]
            kwargs["temperature"] = parameters["temperature"] / 100.0
            kwargs["sequences"] = parameters["sequences"]
            kwargs["top_k"] = parameters["top_k"]
        value = self.generate(
            request_data=data["request_data"],
            **kwargs
        )

        self.engine.send_message(value, code=MessageCode.TEXT_GENERATED)
        self.enable_request_processing()

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
        # if self.model:
        #     self.model.seed = self.seed

    def generate(self, request_data, **kwargs):
        prompt = request_data["prompt"]
        request_type = request_data["request_type"]
        self.username = request_data["username"]
        self.botname = request_data["botname"]
        
        # parse properties
        properties = self.parse_properties(kwargs)
        
        self.do_set_seed(properties.get("seed"))
        self.load_tokenizer()
        self.load_model()

        if self.model is None:
            logger.error("Failed to load model")
            return

        # process the input

        # generate the output
        logger.info("Generating text...")
        if "top_k" in properties and "do_sample" in properties and not properties["do_sample"]:
            del properties["top_k"]
        
        logger.info("Generating output")
        with torch.backends.cuda.sdp_kernel(
            enable_flash=True, 
            enable_math=False, 
            enable_mem_efficient=False
        ):
            with torch.no_grad():
                if self.set_attention_mask:
                    #inputs = self.process_input(input, request_type)
                    attention_mask = torch.ones(inputs.shape)
                    pad_token_id = self.tokenizer.eos_token_id
                    properties["attention_mask"] = attention_mask
                    properties["pad_token_id"] = pad_token_id
                    outputs = self.model.generate(inputs, **properties)
                else:
                    return self.chain.run(prompt)


        # decode the output
        logger.info("decoding output")

        if self.generator.name == "seq2seq":
            value = self.tokenizer.batch_decode(
                outputs,
                skip_special_tokens=kwargs.get("skip_special_tokens", True)
            )[0]
        elif self.generator.name == "casuallm":
            value = self.tokenizer.batch_decode(
                outputs,
                skip_special_tokens=True#kwargs.get("skip_special_tokens", True)
            )[0]
        #tokenizer.batch_decode(gen_tokens[:, input_ids.shape[1]:])[0]

        if request_type == "image_subject_generator":
            return self.generate(value, "image_caption_generator", **kwargs)
        # if request_type == "image_caption_generator":
        #     return self.generate(value, "complete_image_description_generator", **kwargs)
        
        if self.generator.name == "casuallm":
            # strip <<SYS>> tags and anything inside them
            value = re.sub(r'<<SYS>>.*?<<\/SYS>>', '', value, flags=re.DOTALL).strip()

            # strip [INST] tags and anything inside them
            value = re.sub(r'\[INST\].*?\[\/INST\]', '', value, flags=re.DOTALL).strip()

            # strip leading and trailing whitespaces
            value = value.strip()
            value = value.replace('\\n', '')
            value = value.replace('\n', '')
            value = re.sub(r'^\s+', '', value)

        return value

    def parse_properties(self, properties: dict):
        properties["num_beams"] = 1
        properties["temperature"] = 1.0
        data = {
            "max_length": properties.get("max_length", 512),
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
            "decoder_start_token_id": properties.get("decoder_start_token_id", None),
            "use_cache": properties.get("use_cache", None),
        }
        # data = {k: v for k, v in data.items() if v is not None}
        return data


    def process_setting(self, name, val):
        if type(val) == int:
            if name in ["top_p", "ngram_size"]:
                return val / 100
            elif name == "repetition_penalty":
                return val / 10000
            elif name in ["length_penalty", "temperature"]:
                return val / 100
        return val