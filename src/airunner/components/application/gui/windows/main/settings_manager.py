from typing import Any


class SettingsManager:
    """
    Handles application settings logic for MainWindow.
    """

    def __init__(self, app_settings, qsettings, logger=None):
        self.app_settings = app_settings
        self.qsettings = qsettings
        self.logger = logger
        if self.logger:
            self.logger.debug("SettingsManager initialized.")

    def reset_settings(self, main_window):
        if self.logger:
            self.logger.info("Resetting application settings to defaults.")
        self.app_settings.reset_to_defaults()
        if self.logger:
            self.logger.info("Application settings reset to defaults.")
        main_window.restart()

    def update_application_settings(self, key: str, value: Any):
        setattr(self.app_settings, key, value)
        if self.logger:
            self.logger.debug(f"Updated application setting: {key} = {value}")

    def restore_window_state(self, main_window):
        settings = main_window.window_settings
        main_window.setMinimumSize(1024, 1024)
        width = int(settings["width"])
        height = int(settings["height"])
        main_window.resize(width, height)
        x_pos = int(settings["x_pos"])
        y_pos = int(settings["y_pos"])
        main_window.move(x_pos, y_pos)
        if settings.get("is_maximized", False):
            main_window.showMaximized()
        elif settings.get("is_fullscreen", False):
            main_window.showFullScreen()
        else:
            main_window.showNormal()
        main_window.raise_()
        if self.logger:
            self.logger.debug("Restored window state from settings.")
