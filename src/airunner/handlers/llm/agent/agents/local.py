from typing import (
    Optional,
    Type,
)
from PySide6.QtCore import QObject

from transformers import AutoModelForCausalLM, AutoTokenizer

from llama_index.core.llms.llm import LLM

from airunner.handlers.llm.huggingface_llm import HuggingFaceLLM
from airunner.mediator_mixin import MediatorMixin
from airunner.windows.main.settings_mixin import SettingsMixin
from airunner.handlers.llm.agent.agents.base import BaseAgent


class MistralAgentQObject(
    QObject,
    BaseAgent,
    MediatorMixin,
    SettingsMixin,
):
    """QObject wrapper for Mistral Agent"""
    def __init__(
        self, 
        model: Optional[AutoModelForCausalLM] = None,
        tokenizer: Optional[AutoTokenizer] = None,
        *args, 
        **kwargs
    ):
        self.model = model
        self.tokenizer = tokenizer
        MediatorMixin.__init__(self)
        super().__init__(*args, **kwargs)
    
    def unload(self):
        del self.model
        del self.tokenizer
        self.model = None
        self.tokenizer = None
        self._llm = None
        super().unload()
    
    @property
    def llm(self) -> Type[LLM]:
        if not self._llm:
            self.logger.info("Loading HuggingFaceLLM")
            if self.model and self.tokenizer:
                self._llm = HuggingFaceLLM(
                    model=self.model,
                    tokenizer=self.tokenizer,
                    streaming_stopping_criteria=self.streaming_stopping_criteria
                )
            else:
                self.logger.error(
                    "Unable to load HuggingFaceLLM: "
                    "Model and tokenizer must be provided."
                )
        return self._llm
