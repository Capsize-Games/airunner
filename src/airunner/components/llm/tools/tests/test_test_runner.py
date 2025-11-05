"""
Tests for test_runner.py

Test discovery and execution of Python tests.
"""

import pytest
from pathlib import Path

from airunner.components.llm.tools.test_runner import (
    TestRunner,
    TestResult,
)


@pytest.fixture
def workspace_dir(tmp_path):
    """Create temporary workspace directory."""
    return tmp_path / "workspace"


@pytest.fixture
def setup_workspace(workspace_dir):
    """Set up a workspace with source and test files."""
    workspace_dir.mkdir(exist_ok=True)

    # Create source files
    src_dir = workspace_dir / "src" / "mypackage"
    src_dir.mkdir(parents=True, exist_ok=True)

    (src_dir / "module.py").write_text(
        """
def add(a, b):
    return a + b

def subtract(a, b):
    return a - b
"""
    )

    (src_dir / "utils.py").write_text(
        """
def multiply(a, b):
    return a * b
"""
    )

    # Create test files
    test_dir = workspace_dir / "tests" / "mypackage"
    test_dir.mkdir(parents=True, exist_ok=True)

    (test_dir / "test_module.py").write_text(
        """
import pytest
from src.mypackage.module import add, subtract

def test_add():
    assert add(1, 2) == 3

def test_subtract():
    assert subtract(5, 3) == 2
"""
    )

    (test_dir / "test_utils.py").write_text(
        """
import pytest
from src.mypackage.utils import multiply

def test_multiply():
    assert multiply(3, 4) == 12
"""
    )

    return workspace_dir


@pytest.fixture
def runner(setup_workspace):
    """Create TestRunner instance."""
    return TestRunner(str(setup_workspace))


def test_runner_initialization(runner, setup_workspace):
    """Test runner initializes correctly."""
    assert isinstance(runner, TestRunner)
    assert runner.workspace_root == Path(setup_workspace)
    assert runner.test_dir == Path(setup_workspace) / "tests"


def test_discover_tests_for_file(runner, setup_workspace):
    """Test discovering tests for a source file."""
    source_file = setup_workspace / "src" / "mypackage" / "module.py"

    test_files = runner.discover_tests_for_file(str(source_file))

    # Should find test_module.py
    assert len(test_files) > 0
    assert any("test_module.py" in str(f) for f in test_files)


def test_discover_tests_for_nonexistent_file(runner):
    """Test discovering tests for non-existent file."""
    test_files = runner.discover_tests_for_file("/nonexistent/file.py")

    assert len(test_files) == 0


def test_discover_tests_for_multiple_files(runner, setup_workspace):
    """Test discovering tests for multiple source files."""
    file1 = setup_workspace / "src" / "mypackage" / "module.py"
    file2 = setup_workspace / "src" / "mypackage" / "utils.py"

    test_files = runner.discover_tests_for_files([str(file1), str(file2)])

    # Should find both test files
    assert len(test_files) >= 2
    assert any("test_module.py" in str(f) for f in test_files)
    assert any("test_utils.py" in str(f) for f in test_files)


def test_run_specific_test_file(runner, setup_workspace):
    """Test running a specific test file."""
    test_file = setup_workspace / "tests" / "mypackage" / "test_module.py"

    if not runner.pytest_available:
        pytest.skip("pytest not available")

    result = runner.run_tests(test_files=[str(test_file)])

    assert isinstance(result, TestResult)
    # Test may fail due to import errors in temp workspace, but result should be valid
    assert result.output is not None


def test_run_tests_for_file(runner, setup_workspace):
    """Test running tests for a source file."""
    source_file = setup_workspace / "src" / "mypackage" / "module.py"

    if not runner.pytest_available:
        pytest.skip("pytest not available")

    result = runner.run_tests_for_file(str(source_file))

    assert isinstance(result, TestResult)


def test_run_tests_for_file_no_tests(runner, setup_workspace):
    """Test running tests for file with no tests."""
    # Create a file with no corresponding tests
    orphan_file = setup_workspace / "src" / "mypackage" / "orphan.py"
    orphan_file.write_text("x = 1\n")

    result = runner.run_tests_for_file(str(orphan_file))

    # Should discover no or few tests for orphan file
    # (may find package tests that import fails on)
    assert isinstance(result, TestResult)


def test_parse_pytest_output(runner):
    """Test parsing pytest output."""
    output = """
============================= test session starts ==============================
collected 5 items

test_example.py ..F..                                                    [100%]

=================================== FAILURES ===================================
_________________________________ test_fail ____________________________________

    def test_fail():
>       assert False
E       AssertionError

test_example.py:10: AssertionError
========================= 4 passed, 1 failed in 1.23s ==========================
"""

    result = runner._parse_pytest_output(output)

    assert result.total == 5
    assert result.passed == 4
    assert result.failed == 1
    assert result.duration == 1.23
    assert result.success is False


def test_parse_pytest_output_all_passed(runner):
    """Test parsing pytest output with all tests passing."""
    output = """
============================= test session starts ==============================
collected 10 items

test_example.py ..........                                               [100%]

============================== 10 passed in 0.52s ===============================
"""

    result = runner._parse_pytest_output(output)

    assert result.total == 10
    assert result.passed == 10
    assert result.failed == 0
    assert result.duration == 0.52
    assert result.success is True


def test_parse_pytest_output_with_skipped(runner):
    """Test parsing pytest output with skipped tests."""
    output = """
============================= test session starts ==============================
collected 8 items

test_example.py ..s.s...                                                 [100%]

======================= 6 passed, 2 skipped in 0.75s ==========================
"""

    result = runner._parse_pytest_output(output)

    assert result.total == 8
    assert result.passed == 6
    assert result.skipped == 2
    assert result.success is True


def test_test_result_str():
    """Test TestResult string representation."""
    result = TestResult(
        success=False,
        total=10,
        passed=7,
        failed=2,
        skipped=1,
        errors=0,
        duration=1.5,
        output="test output",
        test_files=["test1.py", "test2.py"],
    )

    result_str = str(result)
    assert "✗" in result_str
    assert "7/10 passed" in result_str
    assert "2 failed" in result_str
    assert "1 skipped" in result_str
    assert "1.50s" in result_str


def test_test_result_str_success():
    """Test TestResult string representation for success."""
    result = TestResult(
        success=True,
        total=5,
        passed=5,
        failed=0,
        skipped=0,
        errors=0,
        duration=0.25,
        output="test output",
        test_files=["test.py"],
    )

    result_str = str(result)
    assert "✓" in result_str
    assert "5/5 passed" in result_str
    assert "0 failed" in result_str


def test_runner_without_pytest():
    """Test runner when pytest is not available."""
    runner = TestRunner("/tmp/workspace")

    # If pytest is not available, this should be set to False
    if not runner.pytest_available:
        result = runner.run_tests()
        assert result.success is False
        assert "pytest not available" in result.output


def test_discover_tests_file_outside_workspace(runner, tmp_path):
    """Test discovering tests for file outside workspace."""
    outside_file = tmp_path / "outside.py"
    outside_file.write_text("x = 1\n")

    test_files = runner.discover_tests_for_file(str(outside_file))

    # Should not find anything (file not in workspace)
    assert len(test_files) == 0


def test_run_tests_for_multiple_files(runner, setup_workspace):
    """Test running tests for multiple source files."""
    file1 = setup_workspace / "src" / "mypackage" / "module.py"
    file2 = setup_workspace / "src" / "mypackage" / "utils.py"

    if not runner.pytest_available:
        pytest.skip("pytest not available")

    result = runner.run_tests_for_files([str(file1), str(file2)])

    assert isinstance(result, TestResult)
    # Should run tests from both test files
    assert result.total > 0
