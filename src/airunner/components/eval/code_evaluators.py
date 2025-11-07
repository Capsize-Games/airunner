"""
Code-specific evaluators for HumanEval and other code generation benchmarks.

Provides evaluators that:
- Extract code from LLM responses
- Execute code with test cases
- Evaluate code quality and correctness
"""

import re
import subprocess
import tempfile
from typing import Dict, Any, Optional
from pathlib import Path

from airunner.settings import AIRUNNER_LOG_LEVEL
from airunner.utils.application import get_logger

logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)


def extract_python_code(text: str) -> Optional[str]:
    """Extract Python code from LLM response.

    Looks for code in markdown blocks, or attempts to extract
    function definitions.

    Args:
        text: LLM response text

    Returns:
        Extracted Python code or None
    """
    # Try markdown code blocks first
    code = _extract_from_markdown(text)
    if code:
        return code

    # Try to find function definitions
    if "def " in text:
        return _extract_function_definition(text)

    return None


def _extract_from_markdown(text: str) -> Optional[str]:
    """Extract code from markdown code blocks."""
    # Try python code blocks
    code_block_pattern = r"```python\n(.*?)\n```"
    matches = re.findall(code_block_pattern, text, re.DOTALL)
    if matches:
        return matches[0].strip()

    # Try generic code blocks
    code_block_pattern = r"```\n(.*?)\n```"
    matches = re.findall(code_block_pattern, text, re.DOTALL)
    if matches:
        code = matches[0].strip()
        if "def " in code or "import " in code or "class " in code:
            return code
    return None


def _extract_function_definition(text: str) -> Optional[str]:
    """Extract function definition from text."""
    def_start = text.find("def ")
    if def_start == -1:
        return None

    code_section = text[def_start:]
    lines = code_section.split("\n")
    code_lines = []

    for line in lines:
        # Stop if we hit markdown or explanatory text
        if line.strip().startswith("#") and len(line) > 50:
            break
        if (
            line.strip()
            and not line[0].isspace()
            and not line.startswith("def")
            and not code_lines
        ):
            continue
        code_lines.append(line)
        # Stop after function completes (dedented line after def)
        if (
            code_lines
            and line
            and not line[0].isspace()
            and len(code_lines) > 1
        ):
            break

    if code_lines:
        return "\n".join(code_lines).strip()
    return None


def _create_temp_code_file(code: str, test_code: str) -> Path:
    """Create temporary file with code and tests."""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", delete=False
    ) as f:
        temp_file = Path(f.name)
        full_code = f"{code}\n\n{test_code}\n"
        f.write(full_code)
    return temp_file


def _execute_temp_file(temp_file: Path, timeout: int) -> Dict[str, Any]:
    """Execute temporary Python file and return results."""
    result = subprocess.run(
        ["python", str(temp_file)],
        capture_output=True,
        text=True,
        timeout=timeout,
    )

    success = result.returncode == 0
    output = result.stdout
    error = result.stderr
    tests_passed = success and "AssertionError" not in error

    return {
        "success": success,
        "output": output,
        "error": error,
        "tests_passed": tests_passed,
        "return_code": result.returncode,
    }


def execute_python_code(
    code: str, test_code: str, timeout: int = 5
) -> Dict[str, Any]:
    """Execute Python code with test cases.

    Args:
        code: Python code to test
        test_code: Test code (assertions)
        timeout: Maximum execution time in seconds

    Returns:
        Dict with execution results:
            - success: bool
            - output: str (stdout)
            - error: str (stderr)
            - tests_passed: bool
    """
    temp_file = _create_temp_code_file(code, test_code)

    try:
        return _execute_temp_file(temp_file, timeout)
    except subprocess.TimeoutExpired:
        return _create_timeout_result(timeout)
    except Exception as e:
        return _create_error_result(e)
    finally:
        _cleanup_temp_file(temp_file)


def _create_timeout_result(timeout: int) -> Dict[str, Any]:
    """Create result dict for timeout error."""
    return {
        "success": False,
        "output": "",
        "error": f"Execution timed out after {timeout}s",
        "tests_passed": False,
        "return_code": -1,
    }


def _create_error_result(error: Exception) -> Dict[str, Any]:
    """Create result dict for execution error."""
    return {
        "success": False,
        "output": "",
        "error": f"Execution error: {error}",
        "tests_passed": False,
        "return_code": -1,
    }


def _cleanup_temp_file(temp_file: Path) -> None:
    """Clean up temporary file."""
    try:
        temp_file.unlink()
    except Exception:
        pass


def evaluate_code_correctness(
    prompt: str,
    generated_code: str,
    test_code: str,
    reference_solution: Optional[str] = None,
) -> Dict[str, Any]:
    """Evaluate code correctness by executing tests.

    Args:
        prompt: Original problem prompt
        generated_code: Code generated by LLM
        test_code: Test cases to run
        reference_solution: Optional reference solution

    Returns:
        Evaluation results with score, reasoning, and execution details
    """
    # Extract code from LLM response
    code = extract_python_code(generated_code)

    if not code:
        return _create_no_code_result()

    # Execute code with tests
    exec_result = execute_python_code(code, test_code)

    # Calculate score and create result
    return _create_evaluation_result(exec_result, code)


def _create_no_code_result() -> Dict[str, Any]:
    """Create result when no code is found."""
    return {
        "score": 0.0,
        "reasoning": "No valid Python code found in response",
        "feedback_key": "code_correctness",
        "raw_evaluation": "Failed to extract code",
        "execution": None,
    }


def _create_evaluation_result(
    exec_result: Dict[str, Any], code: str
) -> Dict[str, Any]:
    """Create evaluation result from execution result."""
    if exec_result["tests_passed"]:
        score = 1.0
        reasoning = "All tests passed successfully"
    elif exec_result["success"]:
        score = 0.5
        reasoning = (
            f"Code executed but tests failed: {exec_result['error'][:200]}"
        )
    else:
        score = 0.0
        reasoning = f"Execution failed: {exec_result['error'][:200]}"

    return {
        "score": score,
        "reasoning": reasoning,
        "feedback_key": "code_correctness",
        "raw_evaluation": f"Tests passed: {exec_result['tests_passed']}",
        "execution": exec_result,
        "extracted_code": code,
    }


class CodeCorrectnessEvaluator:
    """Evaluator for code correctness using test execution."""

    def __init__(self):
        self.logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)

    def __call__(
        self,
        inputs: str,
        outputs: str,
        reference_outputs: str,
    ) -> Dict[str, Any]:
        """Evaluate code generation.

        Args:
            inputs: Original problem prompt
            outputs: LLM-generated code
            reference_outputs: Reference solution + tests

        Returns:
            Evaluation results dict
        """
        # Extract test code from reference
        # Reference format: "Solution:\n<code>\n\nTests:\n<tests>"
        test_code = ""
        if "Tests:" in reference_outputs:
            test_code = reference_outputs.split("Tests:")[-1].strip()

        # Extract reference solution
        reference_solution = None
        if "Solution:" in reference_outputs:
            ref_part = reference_outputs.split("Tests:")[0]
            reference_solution = ref_part.replace("Solution:", "").strip()

        return evaluate_code_correctness(
            prompt=inputs,
            generated_code=outputs,
            test_code=test_code,
            reference_solution=reference_solution,
        )


def create_code_correctness_evaluator() -> CodeCorrectnessEvaluator:
    """Create a code correctness evaluator.

    Returns:
        CodeCorrectnessEvaluator instance
    """
    return CodeCorrectnessEvaluator()
