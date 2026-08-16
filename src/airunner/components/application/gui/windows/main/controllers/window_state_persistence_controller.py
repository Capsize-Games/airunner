"""Window geometry persistence for MainWindow."""

from __future__ import annotations

from PySide6.QtGui import QGuiApplication

from airunner.components.application.gui.windows.main.controllers.base import (
    MainWindowBase,
)
from airunner.utils.widgets import save_splitter_settings


class WindowStatePersistenceController(MainWindowBase):
    """Read and write window geometry/state through QSettings."""

    def save_state(self):
        self.logger.debug("Saving window state")
        self.qsettings.beginGroup("window_settings")
        self._save_window_geometry()
        self.qsettings.setValue("active_main_tab_index", 0)
        self.qsettings.setValue(
            "active_left_panel_tab_index", self.ui.left_panel_tab.currentIndex()
        )
        self.qsettings.setValue(
            "active_sidebar_tab_index", self.ui.sidebar_tab.currentIndex()
        )
        self.qsettings.endGroup()
        self.qsettings.sync()
        save_splitter_settings(
            self.ui,
            ["main_window_splitter", "center_splitter"],
            "MainWindow",
        )
        self._save_canvas_offsets()

    def _save_window_geometry(self) -> None:
        """Persist window geometry and screen name."""
        self.qsettings.setValue("is_maximized", self.isMaximized())
        self.qsettings.setValue("is_fullscreen", self.isFullScreen())
        self.qsettings.setValue("width", self.width())
        self.qsettings.setValue("height", self.height())
        self.qsettings.setValue("x_pos", self.pos().x())
        self.qsettings.setValue("y_pos", self.pos().y())
        self._save_screen_name()

    def _save_screen_name(self) -> None:
        """Persist the name of the screen currently hosting the window."""
        try:
            screen = self.screen()
            if screen:
                self.qsettings.setValue("screen_name", screen.name())
        except Exception:
            self.logger.exception("Failed to save screen information")

    def _save_canvas_offsets(self) -> None:
        """Save canvas offsets for all canvas views."""
        try:
            for attr in ("image_canvas", "brush_canvas"):
                canvas = getattr(self.ui, attr, None)
                if canvas is not None:
                    canvas.save_canvas_offset()
        except Exception:
            self.logger.exception("Failed to save canvas offset")

    def restore_state(self):
        """Restore the window based on the previous state using QSettings."""
        state = self._read_window_state()
        target_screen = self._resolve_target_screen(state["screen_name"])
        self._apply_restored_geometry(state, target_screen)
        self.resize(state["width"], state["height"])
        self.setMinimumSize(512, 512)
        if target_screen and self.windowHandle():
            try:
                self.windowHandle().setScreen(target_screen)
            except Exception:
                self.logger.exception("Error re-setting window screen before show")
        self._state_restored = True
        self._apply_window_state(state, target_screen)
        self.raise_()

    def _read_window_state(self) -> dict:
        """Read persisted window geometry/state values."""
        self.qsettings.beginGroup("window_settings")
        state = {
            "is_maximized": self.qsettings.value("is_maximized", False, type=bool),
            "is_fullscreen": self.qsettings.value("is_fullscreen", False, type=bool),
            "width": self._int_value("width", 1024),
            "height": self._int_value("height", 768),
            "x_pos": self._int_value("x_pos", 100),
            "y_pos": self._int_value("y_pos", 100),
            "screen_name": self.qsettings.value("screen_name", None, type=str),
        }
        self.qsettings.endGroup()
        return state

    def _int_value(self, key: str, default: int) -> int:
        """Return one QSettings integer value with a safe default."""
        value = self.qsettings.value(key, default, type=int)
        return value if isinstance(value, int) else default

    def _resolve_target_screen(self, screen_name):
        """Return the matching screen, or None."""
        if not screen_name:
            return None
        try:
            for screen in QGuiApplication.screens():
                if screen.name() == screen_name:
                    return screen
        except Exception:
            self.logger.exception("Error finding target screen")
        self.logger.warning(f"Could not find screen: {screen_name}, using primary")
        return None

    def _apply_restored_geometry(self, state, target_screen) -> None:
        """Move the window to the persisted position on its target screen."""
        x_pos, y_pos = state["x_pos"], state["y_pos"]
        if target_screen:
            try:
                self.create()
                if self.windowHandle():
                    self.windowHandle().setScreen(target_screen)
                    self._move_for_screen(state, target_screen, x_pos, y_pos)
            except Exception:
                self.logger.exception("Error setting window screen")
        else:
            self.move(x_pos, y_pos)

    def _move_for_screen(self, state, screen, x_pos, y_pos) -> None:
        """Move the window onto ``screen`` honoring its persisted state."""
        geometry = screen.geometry()
        if state["is_maximized"] or state["is_fullscreen"]:
            self.move(geometry.x(), geometry.y())
        elif geometry.contains(x_pos, y_pos):
            self.move(x_pos, y_pos)
        else:
            self.move(
                geometry.x() + (geometry.width() - state["width"]) // 2,
                geometry.y() + (geometry.height() - state["height"]) // 2,
            )

    def _apply_window_state(self, state, target_screen) -> None:
        """Apply maximized/fullscreen/normal state after restore."""
        if state["is_maximized"]:
            if target_screen:
                geometry = target_screen.geometry()
                self.move(geometry.x(), geometry.y())
            self.showMaximized()
        elif state["is_fullscreen"]:
            if target_screen:
                geometry = target_screen.geometry()
                self.move(geometry.x(), geometry.y())
            self.showFullScreen()
        else:
            self.showNormal()
