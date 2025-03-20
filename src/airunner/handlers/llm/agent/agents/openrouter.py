from typing import Type

from PySide6.QtCore import QObject

from airunner.mediator_mixin import MediatorMixin
from airunner.windows.main.settings_mixin import SettingsMixin
from llama_index.core.llms.llm import LLM
from llama_index.llms.openrouter import OpenRouter
from airunner.handlers.llm.agent.agents.base import BaseAgent


class OpenRouterAgent(BaseAgent):
    @property
    def llm(self) -> Type[LLM]:
        if not self._llm:
            self._llm = OpenRouter(
                model=self.llm_settings.model,
                api_key=self.llm_settings.openrouter_api_key
            )
        return self._llm


class OpenRouterQObject(
    MediatorMixin,
    SettingsMixin,
    QObject,
    OpenRouterAgent,
):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

