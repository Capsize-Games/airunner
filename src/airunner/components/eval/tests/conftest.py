"""
Pytest configuration for eval tests.

Provides shared fixtures and database setup for all tests.
"""

import os
import pytest
import tempfile
from pathlib import Path

# Import fixtures to make them available to all test files
from airunner.components.eval.fixtures import (
    airunner_server,
    airunner_client,
    airunner_client_function_scope,
)

__all__ = [
    "airunner_server",
    "airunner_client",
    "airunner_client_function_scope",
]


def pytest_addoption(parser):
    """Add custom command line options for pytest.

    Args:
        parser: pytest command line parser
    """
    parser.addoption(
        "--model",
        action="store",
        default=None,
        help="Path to LLM model for testing (e.g., ~/.local/share/airunner/text/models/llm/causallm/Qwen2.5-7B-Instruct)",
    )


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment(request):
    """Configure test environment.

    This fixture runs automatically for all tests (autouse=True) and:
    1. Creates a temporary SQLite database file
    2. Sets AIRUNNER_DATABASE_URL to use this temp database
    3. Sets AIRUNNER_ENVIRONMENT=test
    4. Sets AIRUNNER_TEST_MODEL_PATH from --model flag if provided
    5. Ensures tests don't pollute the user's actual database
    6. Deletes the temp database when tests complete

    The headless server will handle database initialization when it starts.
    Tests can use the /admin/reset_database endpoint to clear state.

    Args:
        request: pytest request fixture to access command line options
    """
    # Create temporary database file
    temp_db = tempfile.NamedTemporaryFile(
        mode="w", suffix=".db", prefix="airunner_test_", delete=False
    )
    temp_db_path = temp_db.name
    temp_db.close()

    # Set environment variables for test mode
    db_url = f"sqlite:///{temp_db_path}"
    os.environ["AIRUNNER_DATABASE_URL"] = db_url
    os.environ["AIRUNNER_ENVIRONMENT"] = "test"

    # Force session_manager to use the test database
    # This must happen AFTER setting the environment variable
    from airunner.components.data.session_manager import reset_engine

    reset_engine()

    # Set model path from --model flag if provided
    model_path = request.config.getoption("--model")
    if model_path:
        # Expand ~ and make absolute
        model_path = os.path.abspath(os.path.expanduser(model_path))
        os.environ["AIRUNNER_TEST_MODEL_PATH"] = model_path
        print(f"\n[TEST CONFIG] Using model: {model_path}")
    else:
        print(
            "\n[TEST CONFIG] WARNING: No --model specified. "
            "LLM tests will fail. "
            "Use: pytest --model=/path/to/model"
        )

    yield

    # Cleanup - delete temporary database file
    try:
        Path(temp_db_path).unlink(missing_ok=True)
    except Exception as e:
        print(f"Warning: Could not delete temp database {temp_db_path}: {e}")
