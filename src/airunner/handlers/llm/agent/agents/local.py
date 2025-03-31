from typing import Optional

from transformers import AutoModelForCausalLM, AutoTokenizer

from airunner.handlers.llm.agent.agents.base import BaseAgent


class LocalAgent(
    BaseAgent
):
    def __init__(
        self, 
        model: Optional[AutoModelForCausalLM] = None,
        tokenizer: Optional[AutoTokenizer] = None,
        *args, 
        **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.model = model
        self.tokenizer = tokenizer