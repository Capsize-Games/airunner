from typing import Annotated
import os
from llama_index.core.tools import FunctionTool
from airunner.handlers.llm.agent.agents.tool_mixins.tool_singleton_mixin import (
    ToolSingletonMixin,
)


class SystemToolsMixin(ToolSingletonMixin):
    """Mixin for system and file tools."""

    @property
    def quit_application_tool(self):
        def quit_application() -> str:
            self.api.quit_application()
            return "Quitting application..."

        return self._get_or_create_singleton(
            "_quit_application_tool",
            FunctionTool.from_defaults,
            quit_application,
            return_direct=True,
        )

    @property
    def toggle_text_to_speech_tool(self):
        def toggle_text_to_speech(
            enabled: Annotated[
                bool,
                ("Enable or disable text to speech. " "Must be 'True' or 'False'."),
            ],
        ) -> str:
            self.api.tts.toggle(enabled)
            return "Text to speech toggled."

        return self._get_or_create_singleton(
            "_toggle_text_to_speech_tool",
            FunctionTool.from_defaults,
            toggle_text_to_speech,
            return_direct=True,
        )

    @property
    def list_files_in_directory_tool(self):
        def list_files_in_directory(
            directory: Annotated[
                str,
                ("The directory to search in. " "Must be a valid directory path."),
            ],
        ) -> str:
            os_path = os.path.abspath(directory)
            if not os.path.isdir(os_path):
                return "Invalid directory path."
            if not os.path.exists(os_path):
                return "Directory does not exist."
            return os.listdir(os_path)

        return self._get_or_create_singleton(
            "_list_files_in_directory_tool",
            FunctionTool.from_defaults,
            list_files_in_directory,
            return_direct=False,
        )
