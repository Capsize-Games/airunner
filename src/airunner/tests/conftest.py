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
    Robust session-scoped fixture for temporary test DB:
    - Creates a temporary database file for the test session.
    - Runs Alembic migrations on that connection.
    - Provides a sessionmaker bound to the same connection for all ORM access.
    - Monkeypatches SQLAlchemy's sessionmaker globally to ensure all code uses this session.
    - Cleans up the temporary database file after tests.
    """
    # Create a temporary database file
    temp_dir = tempfile.mkdtemp()
    temp_db_path = os.path.join(temp_dir, "test_airunner.db")
    db_url = f"sqlite:///{temp_db_path}"

    # Ensure the directory exists
    os.makedirs(os.path.dirname(temp_db_path), exist_ok=True)

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

    # Cleanup
    Session.remove()
    connection.close()
    engine.dispose()

    # Clean up the temporary database file and directory
    try:
        if os.path.exists(temp_db_path):
            os.remove(temp_db_path)
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
    except Exception as e:
        print(f"Warning: Could not clean up temp database: {e}")


@pytest.fixture(scope="session", autouse=True)
def set_test_db_env():
    """
    Set environment variables for test database.
    These will be overridden by the test_db_engine_and_session fixture.
    """
    temp_dir = tempfile.mkdtemp()
    temp_db_path = os.path.join(temp_dir, "test_airunner.db")
    db_url = f"sqlite:///{temp_db_path}"

    os.environ["AIRUNNER_DATABASE_URL"] = db_url
    os.environ["AIRUNNER_DB_NAME"] = temp_db_path
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
