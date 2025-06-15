"""
ContextManager for managing contextual information for the LLM.
Tracks browser tabs, code files, and other sources by unique key.

Google Python Style Guide applies.
"""

from typing import Dict, Any, Optional


class SingletonMeta(type):
    """Metaclass for implementing singleton pattern."""

    _instances: Dict[type, Any] = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]


class ContextManager(metaclass=SingletonMeta):
    """Manages contextual information for the LLM, including browser tabs, code files, and other sources.

    Context is stored as a dictionary keyed by a unique identifier (e.g., URL, file path).
    """

    def __init__(self) -> None:
        self._contexts: Dict[str, Dict[str, Any]] = {}

    def set_context(self, key: str, context: Dict[str, Any]) -> None:
        """Add or update context for a given key.

        Args:
            key (str): Unique identifier for the context (e.g., URL, file path).
            context (dict): Context data.
        """
        self._contexts[key] = context

    def remove_context(self, key: str) -> None:
        """Remove context for a given key.

        Args:
            key (str): Unique identifier for the context.
        """
        self._contexts.pop(key, None)

    def get_context(self, key: str) -> Optional[Dict[str, Any]]:
        """Retrieve context for a given key.

        Args:
            key (str): Unique identifier for the context.

        Returns:
            dict or None: Context data if present.
        """
        return self._contexts.get(key)

    def all_contexts(self) -> Dict[str, Dict[str, Any]]:
        """Get all current contexts.

        Returns:
            dict: All context data.
        """
        return self._contexts

    def clear(self) -> None:
        """Remove all contexts."""
        self._contexts.clear()
