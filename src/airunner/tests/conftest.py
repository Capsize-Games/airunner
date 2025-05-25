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
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session


@pytest.fixture(scope="session", autouse=True)
def test_db_engine_and_session():
    """
    Robust session-scoped fixture for in-memory or test DB:
    - Creates a single engine/connection for the test session.
    - Runs Alembic migrations on that connection.
    - Provides a sessionmaker bound to the same connection for all ORM access.
    - Monkeypatches SQLAlchemy's sessionmaker globally to ensure all code uses this session.
    """
    # Set up DB URL for in-memory or test DB
    db_url = os.environ.get("AIRUNNER_DATABASE_URL", "sqlite:///:memory:")
    engine = create_engine(db_url)
    connection = engine.connect()

    # Run Alembic migrations on this connection
    project_root = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "../../..")
    )
    alembic_ini = os.path.join(project_root, "src", "airunner", "alembic.ini")
    alembic_cfg = Config(alembic_ini)
    alembic_cfg.attributes["connection"] = connection
    alembic_cfg.set_main_option("sqlalchemy.url", db_url)
    command.upgrade(alembic_cfg, "head")

    # Create a sessionmaker bound to this connection
    Session = scoped_session(sessionmaker(bind=connection))

    # Monkeypatch global sessionmaker for all ORM code
    import airunner.data.models.base

    airunner.data.models.base.Session = Session

    yield engine, connection, Session

    Session.remove()
    connection.close()
    engine.dispose()


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


@pytest.fixture(scope="session", autouse=True)
def ensure_qapplication():
    """Ensure a QApplication instance exists for all tests that may require Qt event loop."""
    try:
        from PySide6.QtWidgets import QApplication
    except ImportError:
        pytest.skip("PySide6 is not installed")
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


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
