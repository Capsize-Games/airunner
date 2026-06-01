from types import SimpleNamespace
from typing import Any

from airunner.daemon_client.resource_store import get_resource_store
from airunner.enums import SignalCode


class GridService:
    """Minimal grid service implementation used by unit tests.

    The real application version is more featureful; tests only need a
    get_state and set_position that persist to ActiveGridSettings.
    """

    @staticmethod
    def _settings():
        """Return the persisted active-grid settings record."""
        return get_resource_store().get_singleton("ActiveGridSettings")

    def get_state(self) -> SimpleNamespace:
        settings = self._settings()
        return SimpleNamespace(
            pos_x=getattr(settings, "pos_x", 0),
            pos_y=getattr(settings, "pos_y", 0),
            width=getattr(settings, "width", 0),
            height=getattr(settings, "height", 0),
        )

    def set_position(self, x: int, y: int) -> SimpleNamespace:
        settings = get_resource_store().update_singleton(
            "ActiveGridSettings",
            {"pos_x": x, "pos_y": y},
        )
        payload = {"state": settings}
        self.send(SignalCode.APPLICATION_ACTIVE_GRID_AREA_UPDATED, payload)
        return SimpleNamespace(
            pos_x=getattr(settings, "pos_x", x),
            pos_y=getattr(settings, "pos_y", y),
        )

    # Default send implementation can be overridden in tests
    def send(self, signal: Any, payload: Any) -> None:
        pass
