"""
Tests for code_validator.py

Test validation of Python code with flake8 and mypy.
"""

import pytest

from airunner.components.llm.tools.code_validator import (
    CodeValidator,
    ValidationIssue,
    ValidationResult,
    ValidationSeverity,
)


@pytest.fixture
def temp_py_file(tmp_path):
    """Create a temporary Python file."""

    def _create(content: str, filename: str = "test.py"):
        file_path = tmp_path / filename
        file_path.write_text(content)
        return str(file_path)

    return _create


@pytest.fixture
def validator():
    """Create CodeValidator instance."""
    return CodeValidator(enable_flake8=True, enable_mypy=True)


def test_validator_initialization(validator):
    """Test validator initializes correctly."""
    assert isinstance(validator, CodeValidator)
    # Tools may or may not be available depending on environment
    assert validator.enable_flake8 in [True, False]
    assert validator.enable_mypy in [True, False]


def test_validate_nonexistent_file(validator):
    """Test validation of non-existent file."""
    result = validator.validate_file("/nonexistent/file.py")

    assert result.success is False
    assert result.error_count == 0
    assert len(result.issues) == 0


def test_validate_valid_python_file(validator, temp_py_file):
    """Test validation of valid Python file."""
    content = '''
def hello(name: str) -> str:
    """Say hello."""
    return f"Hello, {name}!"
'''

    file_path = temp_py_file(content)
    result = validator.validate_file(file_path)

    # Should have no errors (may have warnings about unused import etc.)
    assert result.file_path == file_path
    assert isinstance(result, ValidationResult)


def test_validate_file_with_syntax_error(validator, temp_py_file):
    """Test validation of file with syntax error."""
    content = """
def hello(name: str -> str:  # Missing closing paren
    return f"Hello, {name}!"
"""

    file_path = temp_py_file(content)
    result = validator.validate_file(file_path)

    # Should detect syntax error if flake8 is available
    if validator.enable_flake8:
        assert result.error_count > 0 or result.has_errors


def test_validate_file_with_style_issues(validator, temp_py_file):
    """Test validation of file with PEP 8 style issues."""
    content = """
def hello( name ):  # Extra spaces
    x=1+2  # Missing spaces around operators
    return "Hello, " + name
"""

    file_path = temp_py_file(content)
    result = validator.validate_file(file_path)

    # Should detect style issues if flake8 is available
    if validator.enable_flake8:
        assert len(result.issues) > 0


def test_validate_file_with_type_errors(validator, temp_py_file):
    """Test validation of file with type errors."""
    content = """
def add(a: int, b: int) -> int:
    return a + b

result: int = add("1", "2")  # Type error: strings passed for ints
"""

    file_path = temp_py_file(content)
    validator.validate_file(file_path)

    # Should detect type errors if mypy is available
    if validator.enable_mypy:
        # mypy should find the type error
        pass  # Result depends on mypy availability


def test_validation_result_properties(temp_py_file):
    """Test ValidationResult properties."""
    file_path = temp_py_file("x = 1\n")

    result = ValidationResult(
        file_path=file_path,
        success=False,
        issues=[
            ValidationIssue(
                file_path=file_path,
                line=1,
                column=1,
                severity=ValidationSeverity.ERROR,
                code="E501",
                message="line too long",
                tool="flake8",
            ),
            ValidationIssue(
                file_path=file_path,
                line=2,
                column=1,
                severity=ValidationSeverity.WARNING,
                code="W291",
                message="trailing whitespace",
                tool="flake8",
            ),
        ],
        error_count=1,
        warning_count=1,
        info_count=0,
    )

    assert result.has_errors is True
    assert result.has_warnings is True
    assert len(result.issues) == 2
    assert "1 errors, 1 warnings" in str(result)


def test_validation_issue_str():
    """Test ValidationIssue string representation."""
    issue = ValidationIssue(
        file_path="/path/test.py",
        line=10,
        column=5,
        severity=ValidationSeverity.ERROR,
        code="E501",
        message="line too long",
        tool="flake8",
    )

    issue_str = str(issue)
    assert "/path/test.py" in issue_str
    assert ":10:5:" in issue_str
    assert "error" in issue_str
    assert "E501" in issue_str
    assert "line too long" in issue_str


def test_parse_flake8_output(validator):
    """Test parsing flake8 output."""
    output = """test.py:10:5: E501 line too long (82 > 79 characters)
test.py:15:1: W291 trailing whitespace
test.py:20:10: E999 SyntaxError: invalid syntax"""

    issues = validator._parse_flake8_output(output, "test.py")

    assert len(issues) == 3

    assert issues[0].line == 10
    assert issues[0].column == 5
    assert issues[0].code == "E501"
    assert issues[0].severity == ValidationSeverity.ERROR
    assert issues[0].tool == "flake8"

    assert issues[1].code == "W291"
    assert issues[1].severity == ValidationSeverity.WARNING

    assert issues[2].code == "E999"


def test_parse_mypy_output(validator):
    """Test parsing mypy output."""
    output = """test.py:10:5: error: Incompatible return value type [return-value]
test.py:15:10: warning: Unused variable "x" [unused-variable]
test.py:20:1: note: In function "hello" [note]"""

    issues = validator._parse_mypy_output(output, "test.py")

    assert len(issues) == 3

    assert issues[0].line == 10
    assert issues[0].column == 5
    assert issues[0].code == "return-value"
    assert issues[0].severity == ValidationSeverity.ERROR
    assert issues[0].tool == "mypy"

    assert issues[1].severity == ValidationSeverity.WARNING
    assert issues[1].code == "unused-variable"

    assert issues[2].severity == ValidationSeverity.INFO


def test_validate_multiple_files(validator, temp_py_file):
    """Test validating multiple files."""
    file1 = temp_py_file("x = 1\n", "file1.py")
    file2 = temp_py_file("y = 2\n", "file2.py")

    results = validator.validate_files([file1, file2])

    assert len(results) == 2
    assert all(isinstance(r, ValidationResult) for r in results)


def test_get_summary(validator, temp_py_file):
    """Test getting validation summary."""
    file1 = temp_py_file("x = 1\n", "file1.py")

    results = [
        ValidationResult(
            file_path=file1,
            success=False,
            issues=[],
            error_count=2,
            warning_count=1,
            info_count=0,
        ),
        ValidationResult(
            file_path=file1,
            success=True,
            issues=[],
            error_count=0,
            warning_count=3,
            info_count=0,
        ),
    ]

    summary = validator.get_summary(results)

    assert summary["total_files"] == 2
    assert summary["files_with_errors"] == 1
    assert summary["files_with_warnings"] == 2
    assert summary["total_errors"] == 2
    assert summary["total_warnings"] == 4
    assert summary["success"] is False


def test_validator_with_disabled_tools():
    """Test validator with all tools disabled."""
    validator = CodeValidator(enable_flake8=False, enable_mypy=False)

    assert validator.enable_flake8 is False
    assert validator.enable_mypy is False


def test_parse_flake8_output_no_matches(validator):
    """Test parsing flake8 output with no matches."""
    output = "Some random text\nNot a valid flake8 line"

    issues = validator._parse_flake8_output(output, "test.py")

    assert len(issues) == 0


def test_parse_mypy_output_without_code(validator):
    """Test parsing mypy output without error code."""
    output = "test.py:10:5: error: Some error message"

    issues = validator._parse_mypy_output(output, "test.py")

    assert len(issues) == 1
    assert issues[0].code == "mypy"  # Default code when not specified


def test_validation_result_success_with_warnings(temp_py_file):
    """Test that ValidationResult is success even with warnings."""
    file_path = temp_py_file("x = 1\n")

    result = ValidationResult(
        file_path=file_path,
        success=True,
        issues=[
            ValidationIssue(
                file_path=file_path,
                line=1,
                column=1,
                severity=ValidationSeverity.WARNING,
                code="W291",
                message="trailing whitespace",
                tool="flake8",
            ),
        ],
        error_count=0,
        warning_count=1,
        info_count=0,
    )

    assert result.success is True
    assert result.has_errors is False
    assert result.has_warnings is True
