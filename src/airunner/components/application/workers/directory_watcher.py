from PySide6.QtCore import QObject, Signal, QThread

from airunner.utils.application.get_logger import get_logger


class DirectoryWatcher(QObject):
    scan_completed = Signal(bool)

    def __init__(
        self,
        base_path: str,
        scan_function: callable,
    ):
        super().__init__()
        self.logger = get_logger(__name__)
        self.base_path = base_path
        self._scan_function = scan_function
        self._running = True
        self._last_scan_result = None

    def run(self):
        while self._running:
            try:
                force_reload = self._scan_function(self.base_path)
                # Only emit signal when changes are detected or on first run
                if (
                    self._last_scan_result is None
                    or force_reload != self._last_scan_result
                ):
                    self._last_scan_result = force_reload
                    self.scan_completed.emit(force_reload)
                    if force_reload:
                        self.logger.debug(
                            f"Directory changes detected in {self.base_path}"
                        )
            except RuntimeError as e:
                self.logger.error(f"Error emitting scan_completed signal: {e}")
                break
            except Exception as e:
                self.logger.error(f"Error in directory scan: {e}")

            # Sleep longer to reduce CPU usage
            QThread.sleep(2)

    def stop(self):
        """Request the watcher loop to stop."""
        self._running = False
