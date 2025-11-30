"""System control and application tools."""

import json
from typing import Callable

from langchain.tools import tool

from airunner.components.tools.base_tool import BaseTool
from airunner.enums import SignalCode


class SystemTools(BaseTool):
    """Mixin class providing system control and application management tools."""

    def clear_conversation_tool(self) -> Callable:
        """Clear conversation history."""

        @tool
        def clear_conversation() -> str:
            """Clear the current conversation history.

            Returns:
                Confirmation message
            """
            try:
                self.emit_signal(SignalCode.LLM_CLEAR_HISTORY_SIGNAL)
                return "Conversation history cleared"
            except Exception as e:
                return f"Error clearing conversation: {str(e)}"

        return clear_conversation

    def quit_application_tool(self) -> Callable:
        """Quit the application."""

        @tool
        def quit_application() -> str:
            """Quit the AI Runner application.

            Returns:
                Confirmation message
            """
            try:
                self.emit_signal(SignalCode.APPLICATION_QUIT_SIGNAL)
                return "Quitting application..."
            except Exception as e:
                return f"Error quitting application: {str(e)}"

        return quit_application

    def toggle_tts_tool(self) -> Callable:
        """Toggle text-to-speech."""

        @tool
        def toggle_tts(enabled: bool) -> str:
            """Enable or disable text-to-speech.

            Args:
                enabled: True to enable, False to disable

            Returns:
                Confirmation message
            """
            try:
                self.emit_signal(
                    SignalCode.TOGGLE_TTS_SIGNAL, {"enabled": enabled}
                )
                return f"TTS {'enabled' if enabled else 'disabled'}"
            except Exception as e:
                return f"Error toggling TTS: {str(e)}"

        return toggle_tts

    def update_mood_tool(self) -> Callable:
        """Update the chatbot's mood based on conversation."""

        @tool
        def update_mood(mood: str, emoji: str = "😐") -> str:
            """Update the chatbot's emotional state based on the conversation.

            This should be called periodically during conversation to reflect
            how the bot is feeling based on the interaction.

            Args:
                mood: A one-word emotion (e.g., happy, sad, excited, confused, neutral)
                emoji: A single emoji representing the mood (e.g., 😊, 😢, 😡, 😐)

            Returns:
                Confirmation message
            """
            try:
                self.emit_signal(
                    SignalCode.BOT_MOOD_UPDATED,
                    {"mood": mood, "emoji": emoji},
                )
                return f"Mood updated to '{mood}' {emoji}"
            except Exception as e:
                return f"Error updating mood: {str(e)}"

        return update_mood

    def emit_signal_tool(self) -> Callable:
        """Emit application signals to control the UI and system."""

        @tool
        def emit_signal(signal_name: str, data: str = "{}") -> str:
            """Emit a signal to control the application.

            This allows you to trigger application events like generating images,
            toggling features, or updating the UI. Use with caution.

            AVAILABLE SIGNALS (most useful ones):
            - SD_GENERATE_IMAGE_SIGNAL: Generate an image
              Data: {"prompt": "...", "negative_prompt": "..."}

            - CANVAS_CLEAR: Clear the canvas
              Data: {}

            - TOGGLE_TTS_SIGNAL: Toggle text-to-speech
              Data: {}

            - TOGGLE_FULLSCREEN_SIGNAL: Toggle fullscreen mode
              Data: {}

            - LLM_CLEAR_HISTORY_SIGNAL: Clear conversation history
              Data: {}

            - QUIT_APPLICATION: Quit the application (use with confirmation!)
              Data: {}

            Args:
                signal_name: Name of the signal to emit (e.g., "TOGGLE_TTS_SIGNAL")
                data: JSON string with signal data (default: "{}")

            Returns:
                Confirmation or error message
            """
            try:
                # Parse data JSON
                try:
                    data_dict = json.loads(data)
                except json.JSONDecodeError:
                    return f"Error: data must be valid JSON. Got: {data}"

                # Validate signal exists
                try:
                    signal_code = SignalCode[signal_name]
                except KeyError:
                    available = [
                        "SD_GENERATE_IMAGE_SIGNAL",
                        "CANVAS_CLEAR",
                        "TOGGLE_TTS_SIGNAL",
                        "TOGGLE_FULLSCREEN_SIGNAL",
                        "LLM_CLEAR_HISTORY_SIGNAL",
                        "QUIT_APPLICATION",
                    ]
                    return f"Unknown signal '{signal_name}'. Available signals: {', '.join(available)}"

                # Emit the signal
                self.emit_signal(signal_code, data_dict)
                return f"Signal '{signal_name}' emitted successfully"

            except Exception as e:
                self.logger.error(f"Error emitting signal: {e}")
                return f"Error emitting signal: {str(e)}"

        return emit_signal
