import pytest
from PySide6.QtWidgets import QApplication
import gc
from airunner.gui.widgets.llm.local_http_server import LocalHttpServerThread


@pytest.fixture(autouse=True, scope="session")
def teardown_threads_and_qapp():
    yield
    # After all tests, clean up LocalHttpServerThread and QApplication
    for obj in gc.get_objects():
        try:
            if isinstance(obj, LocalHttpServerThread):
                obj.stop()
                obj.wait()
        except Exception:
            pass
    app = QApplication.instance()
    if app is not None:
        app.quit()
