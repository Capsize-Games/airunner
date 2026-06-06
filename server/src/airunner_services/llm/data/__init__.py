"""LLM data models.

Import all models here to ensure SQLAlchemy registers relationships properly.
"""

# Import models to register with SQLAlchemy
from airunner_services.database.models.target_files import (
    TargetFiles,
)  # noqa: F401
from airunner_services.database.models.target_directories import (
    TargetDirectories,
)  # noqa: F401
from airunner_services.database.models.chatbot import Chatbot  # noqa: F401

__all__ = ["TargetFiles", "TargetDirectories", "Chatbot"]
