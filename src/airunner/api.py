from typing import Optional

from airunner.app import App
from airunner.handlers.llm import (
    LLMRequest, 
    LLMResponse
)
from airunner.handlers.stablediffusion import (
    
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
        do_tts_reply: bool = True,
    ):
        """
        Send a request to the LLM with the given prompt and action.
        
        :param prompt: The prompt to send to the LLM.
        :param llm_request: Optional LLMRequest object.
        :param action: The action type for the request.
        :param do_tts_reply: Whether to do text-to-speech reply.
        :return: None
        """
        llm_request = llm_request or LLMRequest.from_default()
        llm_request.do_tts_reply = do_tts_reply

        self.emit_signal(
            SignalCode.LLM_TEXT_GENERATE_REQUEST_SIGNAL,
            {
                "llm_request": True,
                "request_data": {
                    "action": action,
                    "prompt": prompt,
                    "llm_request": llm_request,
                    "do_tts_reply": do_tts_reply,
                }
            }
        )
    
    def send_tts_request(self, response: LLMResponse):
        """
        Send a TTS request with the given response."
        
        :param response: The LLMResponse object.
        :return: None
        """
        self.emit_signal(SignalCode.LLM_TEXT_STREAMED_SIGNAL, {
            "response": response
        })