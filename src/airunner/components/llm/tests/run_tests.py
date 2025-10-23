#!/usr/bin/env python
"""
Test runner for LLM component tests.

Usage:
    python -m airunner.components.llm.tests.run_tests

Or run specific test:
    python -m airunner.components.llm.tests.test_tool_manager
"""
import unittest
import sys
from pathlib import Path


def run_tests():
    """Discover and run all tests in the llm/tests directory."""
    # Get the tests directory
    tests_dir = Path(__file__).parent

    # Discover tests
    loader = unittest.TestLoader()
    suite = loader.discover(
        start_dir=str(tests_dir),
        pattern="test_*.py",
        top_level_dir=str(tests_dir.parent.parent.parent),
    )

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Exit with error code if tests failed
    sys.exit(0 if result.wasSuccessful() else 1)


if __name__ == "__main__":
    run_tests()
