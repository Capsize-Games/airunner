"""
Base test case for AI Runner components.

Provides common test patterns and utilities for component testing.
"""

from typing import Dict, List, Any, Optional
import unittest
from unittest.mock import MagicMock
import tempfile
from pathlib import Path


class BaseTestCase(unittest.TestCase):
    """
    Base test case with common patterns.

    Subclasses should set:
    - target_class: The class being tested
    - public_methods: List of expected public methods
    - public_properties: List of expected public properties
    - _setup_args: Args to pass to constructor
    - _setup_kwargs: Kwargs to pass to constructor
    """

    target_class: Optional[type] = None
    public_methods: List[str] = []
    public_properties: List[str] = []
    _setup_args: List[Any] = []
    _setup_kwargs: Dict[str, Any] = {}

    def setUp(self):
        """Set up test instance."""
        if self.target_class is None:
            self.skipTest(
                "BaseTestCase is abstract and should not run directly"
            )
        self.obj = self.target_class(*self._setup_args, **self._setup_kwargs)

    def tearDown(self):
        """Clean up test instance."""
        if hasattr(self, "obj"):
            del self.obj

    def test_instantiation(self):
        """Test that object can be instantiated."""
        self.assertIsInstance(self.obj, self.target_class)

    def test_has_public_methods(self):
        """Test that all expected public methods exist and are callable."""
        for method in self.public_methods:
            self.assertTrue(
                hasattr(self.obj, method),
                f"{self.target_class.__name__} is missing public method: {method}",
            )
            self.assertTrue(
                callable(getattr(self.obj, method, None)),
                f"{self.target_class.__name__} public method is not callable: {method}",
            )

    def test_has_public_properties(self):
        """Test that all expected public properties exist."""
        for prop in self.public_properties:
            self.assertTrue(
                hasattr(self.obj, prop),
                f"{self.target_class.__name__} is missing public property: {prop}",
            )

    @staticmethod
    def invoke_tool(tool, **kwargs):
        """
        Helper to invoke LangChain tools with keyword arguments.

        Converts kwargs to the format expected by tool.invoke().

        Args:
            tool: The LangChain tool to invoke
            **kwargs: Keyword arguments to pass to the tool

        Returns:
            The result of invoking the tool

        Example:
            result = self.invoke_tool(tool, query="test", limit=5)
        """
        return tool.invoke(kwargs) if kwargs else tool.invoke({})


class DatabaseTestCase(BaseTestCase):
    """
    Base test case for database-dependent tests.

    Provides utilities for database testing.
    """

    @classmethod
    def setUpClass(cls):
        """Set up test database."""
        from airunner.components.data.session_manager import session_scope

        cls.session_scope = session_scope

    def setUp(self):
        """Set up test with database session."""
        super().setUp()

    def create_test_record(self, model_class, **kwargs):
        """Helper to create test database records."""
        with self.session_scope() as session:
            record = model_class(**kwargs)
            session.add(record)
            session.commit()
            session.refresh(record)
            return record

    def count_records(self, model_class):
        """Helper to count records of a type."""
        with self.session_scope() as session:
            return session.query(model_class).count()


class WidgetTestCase(BaseTestCase):
    """
    Base test case for Qt widget tests.

    Handles QApplication setup/teardown.
    """

    @classmethod
    def setUpClass(cls):
        """Set up QApplication for widget tests."""
        from PySide6.QtWidgets import QApplication
        import sys

        # Create QApplication if not exists
        app = QApplication.instance()
        if app is None:
            cls.app = QApplication(sys.argv)
        else:
            cls.app = app

    @classmethod
    def tearDownClass(cls):
        """Clean up QApplication."""
        # Don't quit the app if it was already running


def with_temp_directory(func):
    """
    Decorator that provides a temporary directory.

    Usage:
        @with_temp_directory
        def test_something(self, tmpdir):
            # tmpdir is a Path object
            pass
    """
    from functools import wraps

    @wraps(func)
    def wrapper(self, *args, **kwargs):
        with tempfile.TemporaryDirectory() as tmpdir:
            return func(self, Path(tmpdir), *args, **kwargs)

    return wrapper


def with_mock_settings(func):
    """
    Decorator that provides mock settings object.

    Usage:
        @with_mock_settings
        def test_something(self, mock_settings):
            mock_settings.llm_settings.provider = "test"
            pass
    """
    from functools import wraps

    @wraps(func)
    def wrapper(self, *args, **kwargs):
        mock_settings = MagicMock()
        return func(self, mock_settings, *args, **kwargs)

    return wrapper
