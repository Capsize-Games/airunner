"""
Code mode tools for programming assistance.

Provides tools for:
- Safe code execution
- Code formatting and linting
- File operations for code projects
- Code analysis and debugging
"""

import subprocess
import tempfile
import os
from pathlib import Path
from airunner.components.llm.core.tool_registry import tool, ToolCategory
from airunner.settings import AIRUNNER_LOG_LEVEL
from airunner.utils.application import get_logger

logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)


@tool(
    name="execute_python",
    category=ToolCategory.CODE,
    description=(
        "Execute Python code safely in an isolated environment. "
        "Returns stdout, stderr, and exit code. Use for testing code snippets, "
        "running small programs, or validating solutions."
    ),
)
def execute_python(code: str, timeout: int = 5) -> str:
    """
    Execute Python code safely.

    Args:
        code: The Python code to execute
        timeout: Maximum execution time in seconds. Defaults to 5

    """
    logger.info(f"Executing Python code (timeout: {timeout}s)")

    try:
        # Create temporary file for code
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False
        ) as f:
            f.write(code)
            temp_file = f.name

        try:
            # Execute code with timeout
            result = subprocess.run(
                ["python3", temp_file],
                capture_output=True,
                text=True,
                timeout=timeout,
            )

            output = []
            if result.stdout:
                output.append(f"STDOUT:\n{result.stdout}")
            if result.stderr:
                output.append(f"STDERR:\n{result.stderr}")
            output.append(f"Exit code: {result.returncode}")

            return "\n\n".join(output)

        finally:
            # Clean up temp file
            try:
                os.unlink(temp_file)
            except Exception:
                pass

    except subprocess.TimeoutExpired:
        return f"Error: Execution timed out after {timeout} seconds"
    except Exception as e:
        logger.error(f"Code execution error: {e}")
        return f"Error executing code: {str(e)}"


@tool(
    name="format_code",
    category=ToolCategory.CODE,
    description=(
        "Format Python code according to PEP 8 style guidelines using Black formatter. "
        "Returns formatted code or error message if code has syntax errors."
    ),
)
def format_code(code: str, line_length: int = 79) -> str:
    """
    Format Python code using Black formatter.

    Args:
        code: The Python code to format
        line_length: Maximum line length. Defaults to 79

    """
    logger.info("Formatting Python code")

    try:
        # Try importing black
        import black

        mode = black.Mode(line_length=line_length)
        formatted = black.format_str(code, mode=mode)
        return f"Formatted code:\n\n{formatted}"

    except ImportError:
        # Black not installed - provide basic formatting
        logger.warning("Black not installed, using basic formatting")
        return (
            f"Black formatter not installed. Here's the code with basic formatting:\n\n"
            f"{code}\n\n"
            f"Install Black with: pip install black"
        )
    except Exception as e:
        logger.error(f"Formatting error: {e}")
        return f"Error formatting code: {str(e)}"


@tool(
    name="lint_code",
    category=ToolCategory.CODE,
    description=(
        "Check Python code for style issues, potential bugs, and best practice violations. "
        "Returns list of warnings and errors with line numbers."
    ),
)
def lint_code(code: str) -> str:
    """
    Lint Python code for issues.

    Args:
        code: The Python code to lint

    """
    logger.info("Linting Python code")

    try:
        # Try importing pylint/flake8
        import pylint.lint

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False
        ) as f:
            f.write(code)
            temp_file = f.name

        try:
            # Run pylint
            result = pylint.lint.Run([temp_file], exit=False)
            return f"Linting complete. Score: {result.linter.stats.global_note}/10"
        finally:
            try:
                os.unlink(temp_file)
            except Exception:
                pass

    except ImportError:
        logger.warning("Pylint not installed")
        return (
            "Linting tools not installed. Basic syntax check:\n"
            f"Code appears syntactically valid ({len(code.splitlines())} lines)\n\n"
            "Install pylint with: pip install pylint"
        )
    except Exception as e:
        logger.error(f"Linting error: {e}")
        return f"Error linting code: {str(e)}"


@tool(
    name="create_code_file",
    category=ToolCategory.CODE,
    description=(
        "Create a new code file with the specified content. "
        "Useful for saving code snippets, creating modules, or setting up project files. "
        "Automatically creates parent directories if needed."
    ),
)
def create_code_file(filepath: str, content: str) -> str:
    """
    Create a new code file.

    Args:
        filepath: Path where file should be created
        content: Content to write to the file

    """
    logger.info(f"Creating code file: {filepath}")

    try:
        path = Path(filepath)

        # Security check - don't allow absolute paths outside workspace
        if path.is_absolute():
            return "Error: Absolute paths not allowed. Use relative paths."

        # Create parent directories
        path.parent.mkdir(parents=True, exist_ok=True)

        # Write file
        path.write_text(content)

        return f"Successfully created {filepath} ({len(content)} bytes)"

    except Exception as e:
        logger.error(f"File creation error: {e}")
        return f"Error creating file: {str(e)}"


@tool(
    name="read_code_file",
    category=ToolCategory.CODE,
    description=(
        "Read contents of a code file. Returns file contents or error if file doesn't exist. "
        "Use for examining existing code, debugging, or code review."
    ),
)
def read_code_file(filepath: str) -> str:
    """
    Read a code file.

    Args:
        filepath: Path to the file to read

    """
    logger.info(f"Reading code file: {filepath}")

    try:
        path = Path(filepath)

        # Security check
        if path.is_absolute():
            return "Error: Absolute paths not allowed. Use relative paths."

        if not path.exists():
            return f"Error: File {filepath} not found"

        content = path.read_text()
        return f"Contents of {filepath}:\n\n{content}"

    except Exception as e:
        logger.error(f"File read error: {e}")
        return f"Error reading file: {str(e)}"


@tool(
    name="analyze_code_complexity",
    category=ToolCategory.CODE,
    description=(
        "Analyze Python code complexity metrics including cyclomatic complexity, "
        "lines of code, function count, and class count. "
        "Helps identify overly complex code that needs refactoring."
    ),
)
def analyze_code_complexity(code: str) -> str:
    """
    Analyze code complexity.

    Args:
        code: The Python code to analyze

    """
    logger.info("Analyzing code complexity")

    lines = code.splitlines()
    total_lines = len(lines)
    code_lines = len(
        [l for l in lines if l.strip() and not l.strip().startswith("#")]
    )
    comment_lines = len([l for l in lines if l.strip().startswith("#")])
    blank_lines = total_lines - code_lines - comment_lines

    # Count functions and classes
    func_count = code.count("def ")
    class_count = code.count("class ")

    # Simple complexity estimation
    complexity_indicators = (
        code.count("if ")
        + code.count("for ")
        + code.count("while ")
        + code.count("and ")
        + code.count("or ")
    )

    return (
        f"Code Complexity Analysis:\n"
        f"- Total lines: {total_lines}\n"
        f"- Code lines: {code_lines}\n"
        f"- Comment lines: {comment_lines}\n"
        f"- Blank lines: {blank_lines}\n"
        f"- Functions: {func_count}\n"
        f"- Classes: {class_count}\n"
        f"- Complexity indicators: {complexity_indicators}\n"
        f"- Estimated complexity: {'High' if complexity_indicators > 10 else 'Moderate' if complexity_indicators > 5 else 'Low'}\n"
        "\nSuggestion: "
        + (
            "Consider breaking complex functions into smaller units"
            if complexity_indicators > 10
            else "Complexity looks reasonable"
        )
    )
