"""
Root conftest for AI Runner tests.

This file configures pytest for the entire test suite.
"""

import os
from pathlib import Path

import pytest


os.environ.setdefault("AIRUNNER_TEST_NO_GUI_LAUNCH", "1")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

_GUI_TEST_SUFFIXES = (
    "src/airunner/components/application/tests/"
    "test_searchable_combo_box.py",
    "src/airunner/components/calendar/tests/test_gui.py",
    "src/airunner/components/settings/tests/"
    "test_model_manager_dialog.py",
    "src/airunner/components/settings/tests/"
    "test_model_selector_widget.py",
    "src/airunner/components/settings/tests/"
    "test_service_settings_widget.py",
)
_MANUAL_TEST_SUFFIXES = (
    "src/airunner/components/application/tests/test_minimal_server.py",
    "src/airunner/components/llm/tests/test_download_manager.py",
    "src/airunner/components/llm/tests/test_ministral3_loading.py",
    "src/airunner/components/llm/tests/test_model_download.py",
    "src/airunner/components/llm/tests/test_model_pipeline.py",
)
_EVAL_TEST_PREFIXES = (
    "/src/airunner/components/eval/",
)
_FUNCTIONAL_TEST_PREFIXES = (
    "/src/airunner/components/server/tests/functional/",
)


def _normalize_path(path: object) -> str:
    """Return a collection path in stable POSIX form."""
    return Path(str(path)).as_posix()


def _is_gui_test_path(path: str) -> bool:
    """Return whether a path belongs to a GUI-only test suite."""
    if "/gui/" in path and "/tests" in path:
        return True
    return path.endswith(_GUI_TEST_SUFFIXES)


def _is_manual_test_path(path: str) -> bool:
    """Return whether a path is a manual harness, not a pytest test."""
    return path.endswith(_MANUAL_TEST_SUFFIXES)


def _is_eval_test_path(path: str) -> bool:
    """Return whether a path belongs to the eval test suite."""
    return any(prefix in path for prefix in _EVAL_TEST_PREFIXES)


def _is_functional_test_path(path: str) -> bool:
    """Return whether a path belongs to a functional test suite."""
    return any(prefix in path for prefix in _FUNCTIONAL_TEST_PREFIXES)


def pytest_configure(config: pytest.Config) -> None:
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "trio: mark test to run with trio async backend"
    )
    config.addinivalue_line(
        "markers", "gui: mark Qt widget tests excluded from safe unit runs"
    )


def pytest_ignore_collect(
    collection_path: Path,
    config: pytest.Config,
) -> bool:
    """Skip GUI and manual harness files before pytest imports them."""
    del config
    path = _normalize_path(collection_path)
    if _is_manual_test_path(path):
        return True
    if os.environ.get("AIRUNNER_SKIP_EVAL_TESTS") == "1":
        if _is_eval_test_path(path):
            return True
    if os.environ.get("AIRUNNER_SKIP_FUNCTIONAL_TESTS") == "1":
        if _is_functional_test_path(path):
            return True
    if os.environ.get("AIRUNNER_SKIP_GUI_TESTS") == "1":
        return _is_gui_test_path(path)
    return False


def pytest_collection_modifyitems(
    config: pytest.Config,
    items: list[pytest.Item],
) -> None:
    """Auto-mark GUI test files for explicit selection."""
    del config
    for item in items:
        item_path = _normalize_path(getattr(item, "path", item.fspath))
        if _is_gui_test_path(item_path):
            item.add_marker(pytest.mark.gui)


@pytest.fixture(scope="session")
def anyio_backend() -> str:
    """
    Override the default anyio_backend fixture to only use asyncio.

    This prevents tests from being parametrized with trio, which is not
    installed and not needed for AI Runner.
    """
    return "asyncio"


@pytest.fixture(scope="session")
def qapp():
    """Provide a shared QApplication for Qt widget tests."""
    try:
        from PySide6.QtWidgets import QApplication
    except ImportError:
        pytest.skip("PySide6 not available")

    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app
