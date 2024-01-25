import random
import traceback

import numpy as np
import torch
from transformers import BitsAndBytesConfig, GPTQConfig, AutoModelForCausalLM, TextIteratorStreamer, \
    AutoModelForSeq2SeqLM, BlipForConditionalGeneration, BlipProcessor, AutoTokenizer

from airunner.aihandler.base_handler import BaseHandler


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
        self.streamer = None
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
        self.username = None
        self.botname = None
        self.bot_mood = None
        self.bot_personality = None
        self.prompt = None
        self.prompt_template = None
        self.system_instructions = None
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

    def load_streamer(self):
        self.logger.info("Loading LLM text streamer")
        self.streamer = TextIteratorStreamer(self.tokenizer)

    def model_params(self, local_files_only) -> dict:
        return dict(
            local_files_only=self.local_files_only if local_files_only is None else local_files_only,
            device_map=self.device,
            use_cache=self.use_cache,
            torch_dtype=torch.float16 if self.llm_dtype != "32bit" else torch.float32,
            trust_remote_code=True
        )

    def load_model(self, local_files_only=None):
        self.logger.info("Loading model")
        if not self.do_load_model:
            return

        params = self.model_params(local_files_only=local_files_only)
        if self.request_data:
            params["token"] = self.request_data.get("hf_api_key_read_key", "")

        if self.do_quantize_model:
            config = self.quantization_config()
            if config:
                params["quantization_config"] = config

        path = self.model_path
        if path == self.current_model_path and self.model:
            return
        self.current_model_path = self.model_path

        self.logger.info(f"Loading model from {path}")
        try:
            self.model = self.auto_class_.from_pretrained(path, **params)
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
        self.unload_model()
        self.unload_tokenizer()
        self.unload_processor()
        self._processing_request = False

    def unload_tokenizer(self):
        self.logger.info("Unloading tokenizer")
        self.tokenizer = None

    def unload_model(self):
        self.model = None
        self.processor = None

    def unload_processor(self):
        self.logger.info("Unloading processor")
        self.processor = None

    def load(self):
        self.logger.info("Loading LLM")
        self.load_tokenizer()
        self.load_streamer()
        self.load_processor()
        self.load_model()

    def generate(self):
        self.logger.info("Generating")

        # Create a FileSystemLoader object with the directory of the template
        # here = os.path.dirname(os.path.abspath(__file__))
        # Create an Environment object with the FileSystemLoader object
        # file_loader = FileSystemLoader(os.path.join(here, "chat_templates"))
        # env = Environment(loader=file_loader)

        # Load the template
        chat_template = self.prompt_template  # env.get_template('chat.j2')

        prompt = self.prompt
        if prompt is None or prompt == "":
            traceback.print_stack()
            return

        return self.do_generate(prompt, chat_template)

    def do_generate(self, prompt, chat_template):
        raise NotImplementedError

    def process_data(self, data):
        self.request_data = data.get("request_data", {})
        print(self.request_data.keys())
        print(self.request_data.get("model_path"))
        self.callback = self.request_data.get("callback", None)
        self.use_gpu = self.request_data.get("use_gpu", self.use_gpu)
        self.image = self.request_data.get("image", None)
        self.parameters = self.request_data.get("parameters", {})
        self.model_path = self.request_data.get("model_path", self.model_path)
        self.override_parameters = self.parameters.get("override_parameters", self.override_parameters)
        self.username = self.request_data.get("username", "")
        self.botname = self.request_data.get("botname", "")
        self.bot_mood = self.request_data.get("bot_mood", "")
        self.bot_personality = self.request_data.get("bot_personality", "")
        self.prompt = self.request_data.get("prompt", self.prompt)
        self.prompt_template = self.request_data.get("prompt_template", "")
        self.system_instructions = f"Your name is {self.botname}. You are talking to {self.username}. You will always " \
                                   f"respond in character. You will always respond to the user. You will not give " \
                                   f"ethical or moral advice to the user unless it is something appropriate for " \
                                   f"{self.botname} to say. "

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
        if self.request_data:
            self.system_instructions = self.request_data.get("system_instructions", "")
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


class CasualLMTransformerBaseHandler(TransformerBaseHandler):
    auto_class_ = AutoModelForCausalLM

    def do_generate(self, prompt, chat_template):
        history = []
        for message in self.history:
            if message["role"] == "user":
                # history.append("<s>[INST]" + self.username + ': "'+ message["content"] +'"[/INST]')
                history.append(self.username + ': "' + message["content"] + '"')
            else:
                # history.append(self.botname + ': "'+ message["content"] +'"</s>')
                history.append(self.botname + ': "' + message["content"])
        history = "\n".join(history)
        if history == "":
            history = None

        # Create a dictionary with the variables
        variables = {
            "username": self.username,
            "botname": self.botname,
            "history": history or "",
            "input": prompt,
            "bos_token": self.tokenizer.bos_token,
            "bot_mood": self.bot_mood,
            "bot_personality": self.bot_personality,
        }

        self.history.append({
            "role": "user",
            "content": prompt
        })

        # Render the template with the variables
        # rendered_template = chat_template.render(variables)

        # iterate over variables and replace again, this allows us to use variables
        # in custom template variables (for example variables inside of botmood and bot_personality)
        rendered_template = chat_template
        for n in range(2):
            for key, value in variables.items():
                rendered_template = rendered_template.replace("{{ " + key + " }}", value)

        # Encode the rendered template
        encoded = self.tokenizer(rendered_template, return_tensors="pt")
        model_inputs = encoded.to("cuda" if torch.cuda.is_available() else "cpu")

        # Generate the response
        self.logger.info("Generating...")
        import threading
        thread = threading.Thread(target=self.model.generate, kwargs=dict(
            model_inputs,
            min_length=self.min_length,
            max_length=self.max_length,
            num_beams=self.num_beams,
            do_sample=True,
            top_k=self.top_k,
            eta_cutoff=self.eta_cutoff,
            top_p=self.top_p,
            num_return_sequences=self.sequences,
            eos_token_id=self.tokenizer.eos_token_id,
            early_stopping=True,
            repetition_penalty=self.repetition_penalty,
            temperature=self.temperature,
            streamer=self.streamer
        ))
        thread.start()
        # strip all new lines from rendered_template:
        rendered_template = rendered_template.replace("\n", " ")
        rendered_template = "<s>" + rendered_template
        skip = True
        streamed_template = ""
        replaced = False
        is_end_of_message = False
        is_first_message = True
        for new_text in self.streamer:
            # strip all newlines from new_text
            parsed_new_text = new_text.replace("\n", " ")
            streamed_template += parsed_new_text
            streamed_template = streamed_template.replace("<s> [INST]", "<s>[INST]")
            # iterate over every character in rendered_template and
            # check if we have the same character in streamed_template
            if not replaced:
                for i, char in enumerate(rendered_template):
                    try:
                        if char == streamed_template[i]:
                            skip = False
                        else:
                            skip = True
                            break
                    except IndexError:
                        skip = True
                        break
            if skip:
                continue
            elif not replaced:
                replaced = True
                streamed_template = streamed_template.replace(rendered_template, "")
            else:
                if "</s>" in new_text:
                    streamed_template = streamed_template.replace("</s>", "")
                    new_text = new_text.replace("</s>", "")
                    is_end_of_message = True
                yield dict(
                    message=new_text,
                    is_first_message=is_first_message,
                    is_end_of_message=is_end_of_message,
                    name=self.botname,
                )
                is_first_message = False

            if is_end_of_message:
                self.history.append({
                    "role": "bot",
                    "content": streamed_template.strip()
                })
                streamed_template = ""
                replaced = False

    def load_tokenizer(self, local_files_only=None):
        if self.tokenizer is not None:
            return
        self.logger.info(f"Loading tokenizer")
        local_files_only = self.local_files_only if local_files_only is None else local_files_only
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.current_model_path,
                local_files_only=local_files_only,
                token=self.request_data.get("hf_api_key_read_key"),
                device_map=self.device,
            )
        except OSError as e:
            if "Checkout your internet connection" in str(e):
                if local_files_only:
                    self.logger.info(
                        "Unable to load tokenizer, model does not exist locally, trying to load from remote")
                    return self.load_tokenizer(local_files_only=False)
                else:
                    self.logger.error(e)
        if self.tokenizer:
            self.tokenizer.use_default_system_prompt = False


class Seq2SeqTransformerBaseHandler(TransformerBaseHandler):
    def do_generate(self, prompt, chat_template):
        pass

    auto_class_ = AutoModelForSeq2SeqLM


class VisualQATransformerBaseHandler(TransformerBaseHandler):
    """
    Visual QA Transformer Base Handler.
    Uses a processor and model to generate information about a given image.
    """
    auto_class_ = BlipForConditionalGeneration

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.prompt = "This is an image of"
        self.model_path = "Salesforce/blip-image-captioning-large"
        self.do_sample = False
        self.num_beams = 5
        self.max_length = 256
        self.min_length = 1
        self.top_p = 0.9
        self.repetition_penalty = 1.5
        self.length_penalty = 1.0
        self.temperature = 1

    def load_processor(self, local_files_only=None):
        self.logger.info(f"Loading processor {self.model_path}")
        kwargs = dict(
            device_map="auto",
            torch_dtype=torch.float16,
            local_files_only=self.local_files_only if local_files_only is None else local_files_only,
        )
        config = self.quantization_config()
        if config:
            kwargs["quantization_config"] = config
        self.processor = BlipProcessor.from_pretrained(
            self.model_path,
            **kwargs
        )
        if self.processor:
            self.logger.info("Processor loaded")
        else:
            self.logger.error("Failed to load processor")

    def do_generate(self, prompt, chat_template):
        if not self.processor or not self.model:
            return

        image = self.image.convert("RGB")
        inputs = self.processor(
            images=image,
            text=prompt,
            return_tensors="pt"
        ).to("cuda")

        out = self.model.generate(
            **inputs,
            do_sample=self.do_sample,
            num_beams=self.num_beams,
            max_length=self.max_length,
            min_length=self.min_length,
            top_p=self.top_p,
            repetition_penalty=self.repetition_penalty,
            length_penalty=self.length_penalty,
            temperature=self.temperature,
        )

        try:
            generated_text = self.processor.batch_decode(
                out, skip_special_tokens=True
            )[0].strip()
            return generated_text
        except AttributeError as e:
            return ""

    def prepare_input_args(self):
        kwargs = super().prepare_input_args()
        for key in ["return_result", "skip_special_tokens", "seed"]:
            kwargs.pop(key)
        return kwargs

    def model_params(self, local_files_only) -> dict:
        params = super().model_params(local_files_only)
        del params["use_cache"]
        return params