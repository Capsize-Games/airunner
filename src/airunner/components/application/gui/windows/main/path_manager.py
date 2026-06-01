class PathManager:
    """
    Handles path and script management logic for MainWindow.
    """

    def __init__(self, path_settings, logger=None):
        self.path_settings = path_settings
        self.logger = logger
        if self.logger:
            self.logger.debug("PathManager initialized.")

    def set_path_settings(self, main_window, key, val):
        if self.logger:
            self.logger.debug(f"Setting path: {key} = {val}")
        main_window.update_path_settings(key, val)

    def reset_paths(self, main_window):
        if self.logger:
            self.logger.info("Resetting all paths to defaults.")
        main_window.reset_path_settings()

    def restart(self, main_window):
        if self.logger:
            self.logger.info("Restarting application.")

