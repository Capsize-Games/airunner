"""LLM data models.

Import all models here to ensure SQLAlchemy registers relationships properly.
"""

# Import models to register with SQLAlchemy
from airunner.components.llm.data.target_files import TargetFiles  # noqa: F401
from airunner.components.llm.data.target_directories import (
    TargetDirectories,
)  # noqa: F401
from airunner.components.llm.data.chatbot import Chatbot  # noqa: F401

__all__ = ["TargetFiles", "TargetDirectories", "Chatbot"]
