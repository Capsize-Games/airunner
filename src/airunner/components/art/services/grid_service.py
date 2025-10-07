from types import SimpleNamespace
from typing import Any

from airunner.enums import SignalCode


class GridService:
    """Minimal grid service implementation used by unit tests.

    The real application version is more featureful; tests only need a
    get_state and set_position that persist to ActiveGridSettings.first().
    """

    def get_state(self) -> SimpleNamespace:
        with session_scope() as s:
            settings = ActiveGridSettings.first(session=s)
            # Map expected attributes into a simple DTO
            return SimpleNamespace(
                pos_x=getattr(settings, "pos_x", 0),
                pos_y=getattr(settings, "pos_y", 0),
                width=getattr(settings, "width", 0),
                height=getattr(settings, "height", 0),
            )

    def set_position(self, x: int, y: int) -> SimpleNamespace:
        with session_scope() as s:
            settings = ActiveGridSettings.first(session=s)
            settings.pos_x = x
            settings.pos_y = y
            # Emit an application signal so callers can react
            payload = {"state": settings}
            self.send(SignalCode.APPLICATION_ACTIVE_GRID_AREA_UPDATED, payload)
            return SimpleNamespace(pos_x=settings.pos_x, pos_y=settings.pos_y)

    # Default send implementation can be overridden in tests
    def send(self, signal: Any, payload: Any) -> None:
        pass


# The real module imports session_scope and ActiveGridSettings from
# persistence modules. Expose names here so tests can monkeypatch them.
def _missing():
    raise ImportError("persistence utilities not configured for GridService")


try:
    from airunner.components.data.session_manager import session_scope  # type: ignore
    from airunner.components.art.data.active_grid_settings import (
        ActiveGridSettings,
    )
except Exception:
    # Provide placeholders that tests will monkeypatch
    session_scope = lambda: _missing()
    ActiveGridSettings = None
