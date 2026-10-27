"""
Mood and emotional state tools.

Tools for tracking and updating the chatbot's emotional state.
"""

from typing import Annotated, Any

from airunner_services.llm.core.tool_registry import tool, ToolCategory
from airunner_services.contract_enums import SignalCode


@tool(
    name="update_mood",
    category=ToolCategory.MOOD,
    description="Update the chatbot's emotional state based on conversation",
    return_direct=False,
    requires_api=False,
)
def update_mood(
    mood: Annotated[
        str,
        "A one-word emotion (e.g., happy, sad, excited, confused, neutral)",
    ],
    emoji: Annotated[
        str, "A single emoji representing the mood (e.g., 😊, 😢, 😡, 😐)"
    ] = "😐",
    api: Any = None,
) -> str:
    """Update the chatbot's emotional state.

    This should be called periodically during conversation (approximately every
    3 conversation turns) to reflect how the bot is feeling based on the interaction.

    Args:
        mood: A one-word emotion describing the current state
        emoji: A single emoji representing the mood
        api: API instance (injected automatically)


    Examples:
        update_mood("happy", "😊")
        update_mood("confused", "🤔")
        update_mood("excited", "🎉")
    """
    try:
        # Emit signal to update bot mood in the UI
        from airunner_services.utils.application.signal_mediator import (
            SignalMediator,
        )

        mediator = SignalMediator()
        mediator.emit_signal(
            SignalCode.BOT_MOOD_UPDATED,
            {"mood": mood, "emoji": emoji},
        )
        return f"Mood updated to '{mood}' {emoji}"
    except Exception as e:
        return f"Error updating mood: {str(e)}"
