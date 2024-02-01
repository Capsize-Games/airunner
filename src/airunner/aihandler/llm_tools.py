from transformers import Tool

from airunner.mediator_mixin import MediatorMixin
from airunner.enums import SignalCode, LLMToolName


class BaseTool(Tool, MediatorMixin):
    def __init__(self, *args, **kwargs):
        MediatorMixin.__init__(self)
        super().__init__(*args, **kwargs)


class ApplicationControlTool(BaseTool):
    inputs = ["text"]
    outputs = ["text"]
    signal_code = None

    def __call__(self, *args, **kwargs):
        self.emit(self.signal_code)
        return "emitting signal"


class QuitApplicationTool(ApplicationControlTool):
    description = "This tool quits the application. It takes no input and returns a string."
    name = LLMToolName.QUIT_APPLICATION.value
    signal_code = SignalCode.QUIT_APPLICATION


class StartVisionCaptureTool(ApplicationControlTool):
    description = "This tool turns the camera on - it starts the input feed. It takes no input and returns a string."
    name = LLMToolName.VISION_START_CAPTURE.value
    signal_code = SignalCode.VISION_START_CAPTURE


class StopVisionCaptureTool(ApplicationControlTool):
    description = "This tool turns the camera off - it stops the input feed. It takes no input and returns a string."
    name = LLMToolName.VISION_STOP_CAPTURE.value
    signal_code = SignalCode.VISION_STOP_CAPTURE
