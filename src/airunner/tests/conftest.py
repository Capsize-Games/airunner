import pytest
from PySide6.QtWidgets import QApplication
import gc
from airunner.gui.widgets.llm.local_http_server import LocalHttpServerThread

# --- ADDED: Alembic migration for test DB setup ---
from alembic.config import Config
from alembic import command
import os
import tempfile
import shutil


@pytest.fixture(scope="session", autouse=True)
def apply_migrations():
    # Use the correct path for alembic.ini inside src/airunner
    project_root = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "../../..")
    )
    alembic_ini = os.path.join(project_root, "src", "airunner", "alembic.ini")
    alembic_cfg = Config(alembic_ini)
    command.upgrade(alembic_cfg, "head")
    yield


@pytest.fixture(scope="session", autouse=True)
def set_test_db_env():
    """
    Ensure all tests use an in-memory SQLite database.
    Sets AIRUNNER_DB_NAME and AIRUNNER_DATABASE_URL before any DB/model import.
    This avoids file system issues and cleanup, and works in CI environments.
    """
    os.environ["AIRUNNER_DB_NAME"] = ":memory:"
    os.environ["AIRUNNER_DATABASE_URL"] = "sqlite:///:memory:"
    yield


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
