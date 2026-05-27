"""Abstract interface for model-manager implementations."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class ModelManagerInterface(ABC):
    """Define the minimum load and unload contract for managers."""

    @abstractmethod
    def load_model(self, *args: Any, **kwargs: Any) -> Any:
        """Load a model resource into memory."""
        raise NotImplementedError

    @abstractmethod
    def unload_model(self, *args: Any, **kwargs: Any) -> Any:
        """Unload a model resource from memory."""
        raise NotImplementedError

    @abstractmethod
    def _load_model(self, *args: Any, **kwargs: Any) -> Any:
        """Perform the concrete model-loading work."""
        raise NotImplementedError

    @abstractmethod
    def _unload_model(self, *args: Any, **kwargs: Any) -> Any:
        """Perform the concrete model-unloading work."""
        raise NotImplementedError