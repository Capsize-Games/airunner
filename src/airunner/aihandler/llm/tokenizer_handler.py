import os
from transformers import RagTokenizer
from airunner.aihandler.llm.transformer_base_handler import TransformerBaseHandler
from transformers.models.llama.tokenization_llama_fast import LlamaTokenizerFast
from airunner.enums import SignalCode, ModelType, ModelStatus
from airunner.settings import LLM_TOKENIZER_DEVICE_INDEX
from airunner.utils.get_torch_device import get_torch_device


class TokenizerHandler(TransformerBaseHandler):
    tokenizer_class_ = LlamaTokenizerFast

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.register(SignalCode.LLM_TOKENIZER_LOAD_SIGNAL, self.on_load_tokenizer_signal)
        self.register(SignalCode.LLM_TOKENIZER_UNLOAD_SIGNAL, self.on_unload_tokenizer_signal)

    def on_load_tokenizer_signal(self, _message: dict):
        self.load_tokenizer()

    def on_unload_tokenizer_signal(self, _message: dict):
        self.unload_tokenizer()

    @property
    def chat_template(self):
        return None

    def get_tokenizer_standard_path(self, path) -> str:
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

    def get_tokenizer_cache_path(self, path):
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
        local_path = os.path.join(local_path, "tokenizer", model_name)
        return local_path

    def get_tokenizer_path(self, path):
        if self.do_quantize_model:
            local_path = self.get_tokenizer_cache_path(path)
            if self.cache_llm_to_disk and os.path.exists(local_path):
                return local_path
            else:
                local_path = self.get_tokenizer_standard_path(path)
                print("CHECKING", local_path)
                if os.path.exists(local_path):
                    return local_path
        return path

    def post_load(self):
        self.load_tokenizer()

    def load_tokenizer(self):
        #path = self.get_tokenizer_path(self.current_model_path)
        if self.tokenizer is not None:
            return
        path = self.get_tokenizer_path(self.current_model_path)
        self.logger.debug(f"Loading tokenizer from {path}")
        kwargs = {
            "local_files_only": True,
            "token": self.request_data.get("hf_api_key_read_key"),
            "device_map": get_torch_device(LLM_TOKENIZER_DEVICE_INDEX),
            "trust_remote_code": True,
            "torch_dtype": self.torch_dtype,
            "attn_implementation": "flash_attention_2",
        }
        # if self.do_quantize_model:
        #     config = self.quantization_config()
        #     if config:
        #         kwargs["quantization_config"] = config

        # </s>  [INST]
        if self.chat_template:
            kwargs["chat_template"] = self.chat_template
        try:
            self.emit_signal(
                SignalCode.MODEL_STATUS_CHANGED_SIGNAL, {
                    "model": ModelType.LLM_TOKENIZER,
                    "status": ModelStatus.LOADING,
                    "path": path
                }
            )
            self.tokenizer = self.tokenizer_class_.from_pretrained(
                path,
                **kwargs,
            )
            self.emit_signal(
                SignalCode.MODEL_STATUS_CHANGED_SIGNAL, {
                    "model": ModelType.LLM_TOKENIZER,
                    "status": ModelStatus.LOADED,
                    "path": path
                }
            )
            self.logger.debug("Tokenizer loaded")
        except Exception as e:
            self.logger.error(e)
            self.emit_signal(
                SignalCode.MODEL_STATUS_CHANGED_SIGNAL, {
                    "model": ModelType.LLM_TOKENIZER,
                    "status": ModelStatus.FAILED,
                    "path": path
                }
            )

        if self.tokenizer:
            self.tokenizer.use_default_system_prompt = False
        else:
            self.logger.error("Tokenizer failed to load")


class RAGTokenizerHandler(TokenizerHandler):
    tokenizer_class_ = RagTokenizer
