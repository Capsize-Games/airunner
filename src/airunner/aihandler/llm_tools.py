"""
This module, `llm_tools.py`, contains tools for an LLM agent.
These tools are used to control the application, analyze images,
audio and more.

The tools are implemented as classes, which are generated
using a factory function `create_application_control_tool_class`.
This function takes a description, a name, and a signal code, and returns a
class that inherits from `BaseTool` and `MediatorMixin`.

Each tool class has a `__call__` method that emits a signal when the
tool is used. The application listens for these signals and
responds accordingly.

Tool descriptions must be written in a way that is understandable to an LLM.
These are the commands that an LLM can use to control the application and
the descriptions are meant to be used as a guide for the LLM so that it
is able to select the correct tool for the task at hand.

Classes:
    See below for a list of classes and their descriptions.
"""

from transformers import Tool

from airunner.mediator_mixin import MediatorMixin
from airunner.enums import SignalCode, LLMToolName


class BaseTool(Tool, MediatorMixin):
    """
    Base class for all tools. Adds the `MediatorMixin` to the `Tool` class.
    This allows for signals to be emitted when the tool is used.
    """
    def __init__(self, *args, **kwargs):
        MediatorMixin.__init__(self)
        super().__init__(*args, **kwargs)


def create_application_control_tool_class(description, name, signal_code):
    """
    Factory function to create a class for an application control tool.

    Args:
        description (str): The description of the tool.
        name (str): The name of the tool.
        signal_code (SignalCode): The signal code that the tool emits when used.

    Returns:
        type: A class that represents the tool.
    """
    class ApplicationControlTool(BaseTool):
        inputs = ["text"]
        outputs = ["text"]
        signal_code = None

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)

        def __call__(self, *args, **kwargs):
            self.emit(self.signal_code)
            return "emitting signal"

    ApplicationControlTool.__doc__ = description
    ApplicationControlTool.__name__ = name
    ApplicationControlTool.signal_code = signal_code

    return ApplicationControlTool


QuitApplicationTool = create_application_control_tool_class(
    (
        "Quit the application. No input, returns nothing."
    ),
    LLMToolName.QUIT_APPLICATION.value,
    SignalCode.QUIT_APPLICATION
)


StartVisionCaptureTool = create_application_control_tool_class(
    (
        "Enable camera. No input, returns nothing."
    ),
    LLMToolName.VISION_START_CAPTURE.value,
    SignalCode.VISION_START_CAPTURE
)


StopVisionCaptureTool = create_application_control_tool_class(
    (
        "Disable camera. No input, returns nothing."
    ),
    LLMToolName.VISION_STOP_CAPTURE.value,
    SignalCode.VISION_STOP_CAPTURE
)

StartAudioCaptureTool = create_application_control_tool_class(
    (
        "Enable microphone. No input, returns nothing."
    ),
    LLMToolName.STT_START_CAPTURE.value,
    SignalCode.STT_START_CAPTURE_SIGNAL
)

StopAudioCaptureTool = create_application_control_tool_class(
    (
        "Disable microphone. No input, returns nothing."
    ),
    LLMToolName.STT_STOP_CAPTURE.value,
    SignalCode.STT_STOP_CAPTURE_SIGNAL
)

StartSpeakersTool = create_application_control_tool_class(
    (
        "Enable text to speech. No input, returns nothing."
    ),
    LLMToolName.TTS_ENABLE.value,
    SignalCode.TTS_ENABLE_SIGNAL
)

StopSpeakersTool = create_application_control_tool_class(
    (
        "Disable text to speech. No input, returns nothing."
    ),
    LLMToolName.TTS_DISABLE.value,
    SignalCode.TTS_DISABLE_SIGNAL
)

ProcessVisionTool = create_application_control_tool_class(
    (
        "Process images captured by the camera. "
        "Takes no input and returns a string."
    ),
    LLMToolName.VISION_PROCESS_IMAGES.value,
    SignalCode.VISION_PROCESS_IMAGES
)

ProcessAudioTool = create_application_control_tool_class(
    (
        "Process audio captured by the microphone. "
        "Takes no input and returns a string."
    ),
    LLMToolName.LLM_PROCESS_STT_AUDIO.value,
    SignalCode.LLM_PROCESS_STT_AUDIO_SIGNAL
)

RespondToUserTool = create_application_control_tool_class(
    (
        "This is a default tool. It is the tool to use when no other tool is applicable. "
        "Takes no input and returns nothing."
    ),
    LLMToolName.DEFAULT_TOOL.value,
    SignalCode.LLM_RESPOND_TO_USER_SIGNAL
)
