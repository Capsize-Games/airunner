from typing import Optional

from airunner.app import App
from airunner.handlers.llm.llm_request import LLMRequest


class API(App):    
    def send_llm_request(self, prompt: str, request: Optional[LLMRequest] = None):
        self.app.main_window.send_llm_request(prompt, request)
    
    def quit(self):
        self.app.quit()
