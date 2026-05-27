from types import SimpleNamespace
from typing import Any

from airunner.enums import SignalCode


class GridService:
    """Minimal grid service implementation used by unit tests.

    The real application version is more featureful; tests only need a
    get_state and set_position that persist to ActiveGridSettings.first().
    """

    def get_state(self) -> SimpleNamespace:
        settings = ActiveGridSettings.objects.first()
        if settings is None:
            settings = ActiveGridSettings.objects.create()
        return SimpleNamespace(
            pos_x=getattr(settings, "pos_x", 0),
            pos_y=getattr(settings, "pos_y", 0),
            width=getattr(settings, "width", 0),
            height=getattr(settings, "height", 0),
        )

    def set_position(self, x: int, y: int) -> SimpleNamespace:
        settings = ActiveGridSettings.objects.first()
        if settings is None:
            settings = ActiveGridSettings.objects.create()
        if settings is not None:
            ActiveGridSettings.objects.update(settings.id, pos_x=x, pos_y=y)
            settings.pos_x = x
            settings.pos_y = y
        payload = {"state": settings}
        self.send(SignalCode.APPLICATION_ACTIVE_GRID_AREA_UPDATED, payload)
        return SimpleNamespace(pos_x=getattr(settings, "pos_x", x), pos_y=getattr(settings, "pos_y", y))

    # Default send implementation can be overridden in tests
    def send(self, signal: Any, payload: Any) -> None:
        pass


# The real module imports ActiveGridSettings from persistence modules.
# Expose the name here so tests can monkeypatch it.
def _missing():
    raise ImportError("persistence utilities not configured for GridService")


try:
    from airunner.models.active_grid_settings import (
        ActiveGridSettings,
    )
except Exception:
    # Provide placeholders that tests will monkeypatch
    ActiveGridSettings = None
