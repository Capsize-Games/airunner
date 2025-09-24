from airunner.components.llm.managers.huggingface_llm import HuggingFaceLLM
from airunner.components.llm.managers.llm_request import LLMRequest
from llama_index.core.llms.llm import LLM
from typing import Type


class LLMManagerMixin:
    """
    Mixin for managing LLM instantiation, model, and tokenizer logic.
    """

    def __init__(self):
        self._tokenizer = None
        self._model = None
        self._llm = None
        self._llm_request = None

    @property
    def llm_request(self) -> LLMRequest:
        if not hasattr(self, "_llm_request") or self._llm_request is None:
            self._llm_request = LLMRequest.from_default()
        return self._llm_request

    @llm_request.setter
    def llm_request(self, value: LLMRequest):
        self._llm_request = value

    @property
    def llm(self) -> Type[LLM]:
        if not hasattr(self, "_llm") or self._llm is None:
            if (
                hasattr(self, "model")
                and hasattr(self, "tokenizer")
                and self.model
                and self.tokenizer
            ):
                self.logger.info("Loading HuggingFaceLLM")
                self._llm = HuggingFaceLLM(
                    agent=self,
                    model=self.model,
                    tokenizer=self.tokenizer,
                    streaming_stopping_criteria=getattr(
                        self, "streaming_stopping_criteria", None
                    ),
                )
                self._llm_updated()
            else:
                self.logger.error(
                    "Unable to load HuggingFaceLLM: Model and tokenizer must be provided."
                )
        return self._llm

    @property
    def model(self):
        return getattr(self, "_model", None)

    @model.setter
    def model(self, value):
        self._model = value

    @model.deleter
    def model(self):
        self._model = None

    @property
    def tokenizer(self):
        return getattr(self, "_tokenizer", None)

    @tokenizer.setter
    def tokenizer(self, value):
        self._tokenizer = value

    @tokenizer.deleter
    def tokenizer(self):
        self._tokenizer = None

    def unload_llm(self):
        if hasattr(self, "_llm") and self._llm:
            self._llm.unload()
        self._llm = None
        self._model = None
        self._tokenizer = None
