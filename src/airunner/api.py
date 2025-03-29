from typing import Optional

from airunner.app import App
from airunner.handlers.llm import (
    LLMRequest, 
    LLMResponse
)
from airunner.enums import (
    SignalCode, 
    LLMActionType
)


class API(App):
    def send_llm_request(
        self, 
        prompt: str, 
        llm_request: Optional[LLMRequest] = None,
        action: LLMActionType = LLMActionType.CHAT,
    ):
        self.emit_signal(
            SignalCode.LLM_TEXT_GENERATE_REQUEST_SIGNAL,
            {
                "llm_request": True,
                "request_data": {
                    "action": action,
                    "prompt": prompt,
                    "llm_request": llm_request or LLMRequest.from_default()
                }
            }
        )
    
    def send_tts_request(self, response: LLMResponse):
        self.emit_signal(SignalCode.LLM_TEXT_STREAMED_SIGNAL, {
            "response": response
        })
