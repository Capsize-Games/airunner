from typing import Optional

from airunner.app import App
from airunner.handlers.llm.llm_request import LLMRequest
from airunner.enums import SignalCode, LLMActionType


class API(App):    
    def send_llm_request(self, prompt: str, llm_request: Optional[LLMRequest] = None):
        self.emit_signal(
            SignalCode.LLM_TEXT_GENERATE_REQUEST_SIGNAL,
            {
                "llm_request": True,
                "request_data": {
                    "action": LLMActionType.CHAT,
                    "prompt": prompt,
                    "llm_request": llm_request or LLMRequest.from_default()
                }
            }
        )