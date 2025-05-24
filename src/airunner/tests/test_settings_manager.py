import pytest
from unittest.mock import MagicMock
from airunner.gui.windows.main.settings_manager import SettingsManager


class DummyAppSettings:
    def __init__(self):
        self.reset_called = False
        self.some_setting = None

    def reset_to_defaults(self):
        self.reset_called = True


class DummyMainWindow:
    def __init__(self):
        self.restart_called = False
        self.window_settings = {
            "width": 800,
            "height": 600,
            "x_pos": 10,
            "y_pos": 20,
            "is_maximized": False,
            "is_fullscreen": False,
        }

    def restart(self):
        self.restart_called = True

    def setMinimumSize(self, w, h):
        pass

    def resize(self, w, h):
        self.resized = (w, h)

    def move(self, x, y):
        self.moved = (x, y)

    def showMaximized(self):
        self.maximized = True

    def showFullScreen(self):
        self.fullscreen = True

    def showNormal(self):
        self.normal = True

    def raise_(self):
        self.raised = True


def test_reset_settings():
    app_settings = DummyAppSettings()
    main_window = DummyMainWindow()
    logger = MagicMock()
    sm = SettingsManager(app_settings, MagicMock(), logger=logger)
    sm.reset_settings(main_window)
    assert app_settings.reset_called
    assert main_window.restart_called
    logger.info.assert_called_with("Application settings reset to defaults.")


def test_update_application_settings():
    app_settings = DummyAppSettings()
    sm = SettingsManager(app_settings, MagicMock(), logger=MagicMock())
    sm.update_application_settings("some_setting", 123)
    assert app_settings.some_setting == 123


def test_restore_window_state():
    app_settings = DummyAppSettings()
    main_window = DummyMainWindow()
    logger = MagicMock()
    sm = SettingsManager(app_settings, MagicMock(), logger=logger)
    sm.restore_window_state(main_window)
    assert main_window.resized == (800, 600)
    assert main_window.moved == (10, 20)
    assert main_window.normal
    assert main_window.raised
    logger.debug.assert_called_with("Restored window state from settings.")
