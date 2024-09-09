import os

from transformers import RagTokenizer, AutoTokenizer
from airunner.aihandler.llm.transformer_base_handler import TransformerBaseHandler
from airunner.enums import SignalCode, ModelType, ModelStatus


class TokenizerHandler(TransformerBaseHandler):
    tokenizer_class_ = AutoTokenizer

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.register(SignalCode.LLM_TOKENIZER_LOAD_SIGNAL, self.on_load_tokenizer_signal)
        self.register(SignalCode.LLM_TOKENIZER_UNLOAD_SIGNAL, self.on_unload_tokenizer_signal)

    def on_load_tokenizer_signal(self):
        self.load_tokenizer()

    def on_unload_tokenizer_signal(self):
        self.unload_tokenizer()

    @property
    def chat_template(self):
        return None

    def post_load(self):
        self.load_tokenizer()

    def load_tokenizer(self):
        if self.tokenizer is not None:
            return

        path = self.get_model_path(self.current_bot["model_version"])

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
            self.model_status = ModelStatus.LOADING
            self.tokenizer = self.tokenizer_class_.from_pretrained(
                path,
                **kwargs,
            )
            self.model_status = ModelStatus.LOADED
            self.logger.debug("Tokenizer loaded")
        except Exception as e:
            self.logger.error(e)
            self.model_status = ModelStatus.FAILED

        if self.tokenizer:
            self.tokenizer.use_default_system_prompt = False
        else:
            self.logger.error("Tokenizer failed to load")


class RAGTokenizerHandler(TokenizerHandler):
    tokenizer_class_ = RagTokenizer
