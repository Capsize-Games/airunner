import os

from transformers import AutoTokenizer, RagTokenizer

from airunner.aihandler.llm.transformer_base_handler import TransformerBaseHandler
from airunner.utils import get_torch_device


class TokenizerHandler(TransformerBaseHandler):
    tokenizer_class_ = AutoTokenizer

    @property
    def chat_template(self):
        return None

    def get_tokenizer_cache_path(self, path):
        model_name = path.split("/")[-1]
        current_llm_generator = self.settings.get("current_llm_generator", "")
        if current_llm_generator == "casuallm":
            local_path = self.settings["path_settings"]["llm_casuallm_model_cache_path"]
        elif current_llm_generator == "seq2seq":
            local_path = self.settings["path_settings"]["llm_seq2seq_model_cache_path"]
        elif current_llm_generator == "visualqa":
            local_path = self.settings["path_settings"]["llm_visualqa_model_cache_path"]
        else:
            local_path = self.settings["path_settings"]["llm_misc_model_cache_path"]
        local_path = os.path.join(local_path, "tokenizer", model_name)
        return local_path

    def get_tokenizer_path(self, path):
        local_path = self.get_tokenizer_cache_path(path)
        if self.use_saved_model and os.path.exists(local_path):
            return local_path
        return path

    def post_load(self):
        self.load_tokenizer()

    def load_tokenizer(self, local_files_only=True):
        #path = self.get_tokenizer_path(self.current_model_path)
        if self.tokenizer is not None:
            return
        path = self.current_model_path
        self.logger.debug(f"Loading tokenizer from {path}")
        local_files_only = self.local_files_only if local_files_only is None else local_files_only
        kwargs = {
            "local_files_only": local_files_only,
            "token": self.request_data.get("hf_api_key_read_key"),
            "device_map": get_torch_device(),
            "trust_remote_code": True,
            "torch_dtype": self.torch_dtype,
        }
        # if self.do_quantize_model:
        #     config = self.quantization_config()
        #     if config:
        #         kwargs["quantization_config"] = config

        # </s>  [INST]
        if self.chat_template:
            kwargs["chat_template"] = self.chat_template
        try:
            self.tokenizer = self.tokenizer_class_.from_pretrained(
                path,
                **kwargs,
            )
            self.logger.debug("Tokenizer loaded")
        except OSError as e:
            if "Checkout your internet connection" in str(e):
                if local_files_only:
                    self.logger.warning(
                        "Unable to load tokenizer, model does not exist locally, trying to load from remote"
                    )
                    return self.load_tokenizer(local_files_only=False)
                else:
                    self.logger.error(e)
        except Exception as e:
            self.logger.error(e)

        if self.tokenizer:
            self.tokenizer.use_default_system_prompt = False
        else:
            self.logger.error("Tokenizer failed to load")


class RAGTokenizerHandler(TokenizerHandler):
    tokenizer_class_ = RagTokenizer
