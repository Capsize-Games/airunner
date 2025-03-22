from typing import Type
from llama_index.core.llms.llm import LLM

from airunner.handlers.llm.agent.agents.base import BaseAgent


class OpenAI(BaseAgent):
    def llm(self) -> Type[LLM]:
        if not self._llm:
            self._llm = OpenAI(
                base_url="",
                api_key=self.llm_settings.openai_api_key
            )
        return self._llm
    
    def chat(self, prompt: str):
        completion = self.llm.chat.completions.create(
            extra_body={},
            model="",
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )
        print(completion.choices[0].message.content)


