import os
import tempfile
import shutil
import pytest


@pytest.fixture(scope="session", autouse=True)
def set_test_db_env():
    """
    Ensure all utils tests use an in-memory SQLite database.
    Sets AIRUNNER_DB_NAME and AIRUNNER_DATABASE_URL before any DB/model import.
    This avoids file system issues and cleanup, and works in CI environments.
    """
    os.environ["AIRUNNER_DB_NAME"] = ":memory:"
    os.environ["AIRUNNER_DATABASE_URL"] = "sqlite:///:memory:"
    yield


# Shared fixtures for utils tests can be placed here.
