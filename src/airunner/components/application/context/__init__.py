"""Application context management module.

Provides services for tracking application state that the LLM
needs to be aware of, including UI section context.
"""

from airunner.components.application.context.ui_context_tracker import (
    UIContextTracker,
    get_ui_context_tracker,
)

__all__ = [
    "UIContextTracker",
    "get_ui_context_tracker",
]
