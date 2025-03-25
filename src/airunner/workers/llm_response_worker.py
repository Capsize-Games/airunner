from typing import Dict

from airunner.enums import SignalCode
from airunner.workers.worker import Worker


class LLMResponseWorker(Worker):
    def __init__(self, *args, **kwargs):
        self.signal_handlers = {
            SignalCode.LLM_TEXT_STREAMED_SIGNAL: self.on_llm_text_streamed,
            SignalCode.INTERRUPT_PROCESS_SIGNAL: self.on_interrupt_process,
        }
        super().__init__(*args, **kwargs)
        self._do_interrupt: bool = False
    
    def on_llm_text_streamed(self, data: Dict):
        if not self._do_interrupt:
            self.add_to_queue(data)
    
    def handle_message(self, data: Dict):
        if not self._do_interrupt:
            self.emit_signal(SignalCode.LLM_TEXT_STREAM_PROCESS_SIGNAL, data)
    
    def on_interrupt_process(self):
        self._do_interrupt = True
        self.clear_queue()
        self._do_interrupt = False