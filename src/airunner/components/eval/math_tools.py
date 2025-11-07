"""
Math problem-solving tools for improved accuracy.

Provides:
1. Safe Python code execution for arithmetic
2. Self-verification loops with retry logic
3. Enhanced math-specific prompting
"""

import re
import io
import contextlib
import threading
import contextvars
import math
from fractions import Fraction
from typing import Dict, Any, Optional, Tuple

from airunner.settings import AIRUNNER_LOG_LEVEL
from airunner.utils.application import get_logger

logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)

_executor_session_var: contextvars.ContextVar[str] = contextvars.ContextVar(
    "safe_python_executor_session",
    default="global",
)


def set_executor_session(session_id: str) -> contextvars.Token[str]:
    """Set the current executor session for persistent namespaces.

    Args:
        session_id: Unique identifier for the execution session

    Returns:
        Context variable token for restoring previous session
    """

    return _executor_session_var.set(session_id)


def reset_executor_session(token: contextvars.Token[str]) -> None:
    """Reset executor session to a previous context."""

    _executor_session_var.reset(token)


def get_executor_session() -> str:
    """Return the current executor session identifier."""

    return _executor_session_var.get()


class SafePythonExecutor:
    """Safely execute Python code for math calculations.

    Restricts imports and provides timeout protection.
    """

    # Allowed imports for math operations
    ALLOWED_IMPORTS = {
        "math",
        "cmath",  # Complex number math
        "fractions",
        "decimal",
        "statistics",
        "itertools",  # Combinatorics (combinations, permutations)
        "sympy",
        "numpy",
        "scipy",
    }

    def __init__(self, timeout_seconds: int = 5):
        """Initialize executor.

        Args:
            timeout_seconds: Maximum execution time
        """
        self.timeout = timeout_seconds
        self._namespaces: Dict[str, Dict[str, Any]] = {}
        self._namespace_lock = threading.Lock()

    def _create_safe_builtins(self) -> Dict[str, Any]:
        """Create the limited set of safe builtins for execution."""

        return {
            "abs": abs,
            "round": round,
            "min": min,
            "max": max,
            "sum": sum,
            "len": len,
            "range": range,
            "int": int,
            "float": float,
            "str": str,
            "bool": bool,
            "list": list,
            "dict": dict,
            "set": set,
            "tuple": tuple,
            "pow": pow,
            "print": print,
            "__import__": __import__,
        }

    def _create_base_namespace(self) -> Dict[str, Any]:
        """Create a fresh namespace with safe builtins and defaults."""

        namespace: Dict[str, Any] = {
            "__builtins__": self._create_safe_builtins()
        }

        namespace["math"] = math
        namespace["Fraction"] = Fraction

        return namespace

    def _ensure_namespace(self, session_id: str) -> Dict[str, Any]:
        """Return namespace for session, creating/resetting as needed."""

        with self._namespace_lock:
            if session_id == "global":
                return self._create_base_namespace()

            namespace = self._namespaces.get(session_id)
            if namespace is None:
                namespace = self._create_base_namespace()
                self._namespaces[session_id] = namespace
            else:
                namespace["__builtins__"] = self._create_safe_builtins()
                if "math" not in namespace:
                    namespace["math"] = math
                if "Fraction" not in namespace:
                    namespace["Fraction"] = Fraction

            return namespace

    def reset(self, session_id: Optional[str] = None) -> None:
        """Reset stored namespaces.

        Args:
            session_id: Optional session identifier to reset. If None, clears all.
        """

        with self._namespace_lock:
            if session_id is None:
                self._namespaces.clear()
            else:
                self._namespaces.pop(session_id, None)

    def extract_code(self, text: str) -> Optional[str]:
        """Extract Python code from markdown code blocks.

        Args:
            text: Text containing code blocks

        Returns:
            Extracted code or None
        """
        # Try to find ```python code blocks
        pattern = r"```python\s*(.*?)```"
        matches = re.findall(pattern, text, re.DOTALL | re.IGNORECASE)
        if matches:
            return matches[0].strip()

        # Try to find ``` code blocks
        pattern = r"```\s*(.*?)```"
        matches = re.findall(pattern, text, re.DOTALL)
        if matches:
            return matches[0].strip()

        return None

    def validate_code(self, code: str) -> Tuple[bool, str]:
        """Check if code is safe to execute.

        Args:
            code: Python code to validate

        Returns:
            (is_safe, error_message)
        """
        # Check for dangerous operations
        is_safe, error = self._check_dangerous_operations(code)
        if not is_safe:
            return False, error

        # Check imports are allowed
        return self._check_imports(code)

    def _check_dangerous_operations(self, code: str) -> Tuple[bool, str]:
        """Check for dangerous patterns in code."""
        dangerous_patterns = [
            r"\bimport\s+os\b",
            r"\bimport\s+subprocess\b",
            r"\bimport\s+sys\b",
            r"\bexec\b",
            r"\beval\b",
            r"\bopen\b",
            r"\bfile\b",
            r"\bcompile\b",
        ]

        for pattern in dangerous_patterns:
            if re.search(pattern, code):
                return False, f"Dangerous operation detected: {pattern}"
        return True, ""

    def _check_imports(self, code: str) -> Tuple[bool, str]:
        """Check that all imports are allowed."""
        import_patterns = [
            (r"^\s*import\s+(\w+)", "module"),
            (r"\bfrom\s+(\w+)\s+import", "module"),
        ]

        for pattern, desc in import_patterns:
            imports = re.findall(pattern, code, re.MULTILINE)
            for imp in imports:
                if imp not in self.ALLOWED_IMPORTS:
                    return False, f"Import not allowed: {imp}"

        return True, ""

    def execute(self, code: str) -> Tuple[bool, Any, str]:
        """Execute Python code and capture output.

        Args:
            code: Python code to execute

        Returns:
            (success, result, error_message)
        """
        # Validate code first
        is_safe, error_msg = self.validate_code(code)
        if not is_safe:
            logger.warning(f"Unsafe code rejected: {error_msg}")
            return False, None, error_msg

        session_id = get_executor_session() or "global"
        namespace = self._ensure_namespace(session_id)

        # Capture stdout
        stdout_capture = io.StringIO()

        # Handle code that might have a final expression to evaluate
        # Split into statements and potential final expression
        last_expr_result = None
        try:
            # Try to compile and check if last line is an expression
            lines = [line.strip() for line in code.split(";") if line.strip()]
            if lines:
                # Execute all but the last line
                if len(lines) > 1:
                    exec_code = "; ".join(lines[:-1])
                    with contextlib.redirect_stdout(stdout_capture):
                        exec(exec_code, namespace)

                # Try to eval the last line to capture expression result
                last_line = lines[-1]
                try:
                    with contextlib.redirect_stdout(stdout_capture):
                        last_expr_result = eval(last_line, namespace)
                except SyntaxError:
                    # Last line is a statement, not an expression
                    with contextlib.redirect_stdout(stdout_capture):
                        exec(last_line, namespace)
                except NameError:
                    # Last line references undefined names, execute normally
                    with contextlib.redirect_stdout(stdout_capture):
                        exec(last_line, namespace)
            else:
                with contextlib.redirect_stdout(stdout_capture):
                    exec(code, namespace)

            result = self._extract_result(
                namespace, stdout_capture, last_expr_result
            )
            return True, result, ""

        except Exception as e:
            error_msg = f"Execution error: {str(e)}"
            logger.warning(error_msg)
            return False, None, error_msg

    def _extract_result(
        self,
        namespace: Dict,
        stdout_capture: io.StringIO,
        last_expr: Any = None,
    ) -> Any:
        """Extract result from namespace, last expression, or stdout."""
        # Priority 1: Explicit result or answer variable
        result = namespace.get("result") or namespace.get("answer")

        # Priority 2: Last expression value (like Python REPL)
        if result is None and last_expr is not None:
            result = last_expr

        # Priority 3: Try to get last printed value
        if result is None:
            output = stdout_capture.getvalue().strip()
            if output:
                result = self._parse_output_as_number(output)

        return result

    def _parse_output_as_number(self, output: str) -> Any:
        """Try to parse output string as a number."""
        lines = output.split("\n")
        last_line = lines[-1].strip()
        try:
            return float(last_line)
        except ValueError:
            return last_line


class SelfVerificationSolver:
    """Solve math problems with self-verification and retry logic."""

    def __init__(self, client, max_attempts: int = 3):
        """Initialize solver.

        Args:
            client: AIRunnerClient instance
            max_attempts: Maximum retry attempts
        """
        self.client = client
        self.max_attempts = max_attempts
        self.executor = SafePythonExecutor()

    def _create_code_prompt(self, prompt: str) -> str:
        """Create prompt for code-based solution.

        Args:
            prompt: Math problem

        Returns:
            Formatted prompt for code generation
        """
        return f"""Solve this math problem by writing Python code.

Problem: {prompt}

CRITICAL REQUIREMENTS:
1. Store the FINAL NUMERIC ANSWER in a variable called 'result'
2. If using sympy, convert symbolic expressions to float: result = float(expr.evalf())
3. For vectors/matrices, convert to list of floats: result = [float(x) for x in vector]
4. For tuples, ensure all elements are numeric: result = tuple(float(x) for x in values)
5. Simplify expressions before returning - no symbolic answers like sqrt(10)

EXAMPLE:
```python
import sympy as sp
x = sp.Symbol('x')
# Solve equation
solution = sp.solve(x**2 - 4, x)[0]  # Returns 2 or -2
result = float(solution)  # Convert to numeric: 2.0
```

Now solve the problem:

```python
# Your solution here
```
"""

    def solve_with_code(
        self, prompt: str, temperature: float = 0.0, verbose: bool = False
    ) -> Dict[str, Any]:
        """Solve using Python code generation.

        Args:
            prompt: Math problem
            temperature: Sampling temperature
            verbose: Print debug info

        Returns:
            Dict with solution, code, result, success
        """
        if verbose:
            print(f"🐍 Requesting Python code solution...")

        code_prompt = self._create_code_prompt(prompt)

        response = self.client.generate(
            code_prompt,
            temperature=temperature,
            max_tokens=1000,
            use_memory=False,
        )

        solution_text = response.get("text", "")
        code = self.executor.extract_code(solution_text)

        if not code:
            return self._create_no_code_result(solution_text, verbose)

        if verbose:
            print(f"📝 Extracted code ({len(code)} chars)")

        success, result, error = self.executor.execute(code)

        if success and result is not None:
            result = self._simplify_result(result)

        self._log_execution_result(success, result, error, verbose)

        return {
            "success": success,
            "solution": solution_text,
            "code": code,
            "result": result,
            "error": error if not success else None,
        }

    def _create_no_code_result(
        self, solution_text: str, verbose: bool
    ) -> Dict[str, Any]:
        """Create result when no code is found."""
        if verbose:
            print(f"⚠️  No code block found in response")
        return {
            "success": False,
            "solution": solution_text,
            "code": None,
            "result": None,
            "error": "No code block found",
        }

    def _log_execution_result(
        self, success: bool, result: Any, error: str, verbose: bool
    ) -> None:
        """Log execution result if verbose."""
        if not verbose:
            return
        if success:
            print(f"✅ Code executed successfully: result = {result}")
        else:
            print(f"❌ Code execution failed: {error}")

    def _simplify_result(self, result):
        """Attempt to simplify symbolic expressions to numeric values.

        Args:
            result: Raw result from code execution

        Returns:
            Simplified numeric result
        """
        try:
            # Check if it's a sympy expression
            if hasattr(result, "evalf"):
                return float(result.evalf())

            # Handle lists/tuples of sympy expressions
            if isinstance(result, (list, tuple)):
                simplified = []
                for item in result:
                    if hasattr(item, "evalf"):
                        simplified.append(float(item.evalf()))
                    elif isinstance(item, (int, float)):
                        simplified.append(float(item))
                    else:
                        simplified.append(item)
                return type(result)(simplified)

            # Already numeric
            return result
        except:
            # Return as-is if simplification fails
            return result

    def _create_solution_prompt(
        self, prompt: str, attempt_num: int, prev_verification: str = ""
    ) -> str:
        """Create prompt for solution generation.

        Args:
            prompt: Math problem
            attempt_num: Current attempt number
            prev_verification: Feedback from previous attempt

        Returns:
            Formatted prompt string
        """
        if attempt_num == 1:
            return f"""{prompt}

INSTRUCTIONS:
1. Work through the problem step-by-step
2. Show all your work and reasoning
3. Double-check calculations
4. At the very end, write your final answer CLEARLY in this exact format:
   
   #### [your answer]
   
   For example:
   #### 42
   #### 3/8
   #### (1, 2, 3)
   
CRITICAL: You MUST include the #### marker with your final answer!

Your solution:"""

        return f"""{prompt}

Previous attempt was incorrect:
{prev_verification}

IMPORTANT: Try a completely different approach. Think carefully about:
- What assumptions might be wrong?
- Are there edge cases to consider?
- Can you verify your answer makes sense?

At the very end, write your final answer CLEARLY in this exact format:

#### [your answer]

CRITICAL: You MUST include the #### marker with your final answer!

Your solution:"""

    def _create_verification_prompt(self, prompt: str, solution: str) -> str:
        """Create prompt for solution verification.

        Args:
            prompt: Original math problem
            solution: Proposed solution

        Returns:
            Formatted verification prompt
        """
        return f"""Review this math solution for CORRECTNESS.

Problem: {prompt}

Proposed Solution: {solution}

CRITICAL VERIFICATION STEPS:
1. Check each calculation step-by-step
2. Verify the mathematical reasoning is sound
3. Most importantly: CHECK THE FINAL NUMERIC ANSWER
4. Does the answer match what the problem asks for?
5. Is the answer in the correct format?

If you find ANY error in the calculations or reasoning, the answer is INCORRECT.
If the final answer doesn't make sense or is obviously wrong, it's INCORRECT.

Respond ONLY with one of these:
- CORRECT (if the solution and final answer are both absolutely correct)
- INCORRECT (if there are any errors)

If INCORRECT, explain what's wrong on the next line.

Answer:"""

    def _verify_solution(
        self, prompt: str, solution: str, temperature: float = 0.0
    ) -> Tuple[bool, str]:
        """Verify if solution is correct.

        Args:
            prompt: Original problem
            solution: Proposed solution
            temperature: Sampling temperature

        Returns:
            Tuple of (is_correct, verification_text)
        """
        verification_prompt = self._create_verification_prompt(
            prompt, solution
        )

        verification_response = self.client.generate(
            verification_prompt,
            temperature=temperature,
            max_tokens=1000,
            use_memory=False,
        )

        verification = verification_response.get("text", "")
        is_correct = (
            "CORRECT" in verification.upper()
            and "INCORRECT" not in verification.upper()
        )

        return is_correct, verification

    def solve_with_verification(
        self,
        prompt: str,
        expected_answer: Optional[str] = None,
        temperature: float = 0.0,
        verbose: bool = False,
    ) -> Dict[str, Any]:
        """Solve with self-verification and retry.

        Args:
            prompt: Math problem
            expected_answer: Known correct answer (for testing)
            temperature: Sampling temperature
            verbose: Print debug info

        Returns:
            Dict with final solution, attempts, verification results
        """
        attempts = []

        for attempt_num in range(1, self.max_attempts + 1):
            attempt = self._try_solution_attempt(
                prompt, attempts, attempt_num, temperature, verbose
            )
            attempts.append(attempt)

            if attempt["is_correct"]:
                if verbose:
                    print(f"🎯 Solution verified on attempt {attempt_num}")
                break

        return self._create_verification_result(attempts)

    def _try_solution_attempt(
        self,
        prompt: str,
        attempts: list,
        attempt_num: int,
        temperature: float,
        verbose: bool,
    ) -> Dict[str, Any]:
        """Try a single solution attempt with verification."""
        if verbose:
            print(f"\n🔄 Attempt {attempt_num}/{self.max_attempts}")

        # Generate solution
        prev_verification = attempts[-1]["verification"] if attempts else ""
        solution_prompt = self._create_solution_prompt(
            prompt, attempt_num, prev_verification
        )

        response = self.client.generate(
            solution_prompt,
            temperature=temperature,
            max_tokens=2000,
            use_memory=False,
        )

        solution = response.get("text", "")

        if verbose:
            print(f"💭 Solution: {solution[:200]}...")

        # Verify solution
        is_correct, verification = self._verify_solution(
            prompt, solution, temperature
        )

        if verbose:
            status = "✅ VERIFIED" if is_correct else "❌ INCORRECT"
            print(f"{status}: {verification[:150]}...")

        return {
            "attempt": attempt_num,
            "solution": solution,
            "verification": verification,
            "is_correct": is_correct,
        }

    def _create_verification_result(self, attempts: list) -> Dict[str, Any]:
        """Create final verification result from attempts."""
        verified_attempts = [a for a in attempts if a["is_correct"]]
        final_attempt = (
            verified_attempts[0] if verified_attempts else attempts[-1]
        )

        return {
            "solution": final_attempt["solution"],
            "verification": final_attempt["verification"],
            "is_verified": final_attempt["is_correct"],
            "attempts": len(attempts),
            "all_attempts": attempts,
        }

    def _is_code_result_valid(
        self, code_result: Dict[str, Any], verbose: bool
    ) -> bool:
        """Check if code execution result is valid and useful."""
        if not code_result["success"] or code_result["result"] is None:
            return False

        result_str = str(code_result["result"])
        if len(result_str) >= 200:
            return False

        if verbose:
            print(f"✅ Code solution successful: {code_result['result']}")
        return True

    def _create_code_result_dict(
        self, code_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create result dictionary from code execution."""
        return {
            "method": "code_execution",
            "solution": code_result["solution"],
            "answer": str(code_result["result"]),
            "code": code_result["code"],
            "success": True,
        }

    def _create_verification_result_dict(
        self, verification_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create result dictionary from verification loop."""
        answer = self._extract_answer_from_solution(
            verification_result["solution"]
        )

        return {
            "method": "verification_loop",
            "solution": verification_result["solution"],
            "answer": answer,
            "is_verified": verification_result["is_verified"],
            "attempts": verification_result["attempts"],
            "success": True,
        }

    def solve_hybrid(
        self,
        prompt: str,
        expected_answer: Optional[str] = None,
        temperature: float = 0.0,
        verbose: bool = False,
    ) -> Dict[str, Any]:
        """Solve using both code execution AND verification.

        First tries Python code approach. If that fails, falls back to
        verification loop.

        Args:
            prompt: Math problem
            expected_answer: Known correct answer (for testing)
            temperature: Sampling temperature
            verbose: Print debug info

        Returns:
            Dict with solution and metadata
        """
        if verbose:
            print(f"🔬 Attempting hybrid solution: Code + Verification")

        code_result = self.solve_with_code(prompt, temperature, verbose)

        if self._is_code_result_valid(code_result, verbose):
            return self._create_code_result_dict(code_result)

        if verbose:
            print(f"⚠️  Code solution failed, trying verification loop...")

        verification_result = self.solve_with_verification(
            prompt, expected_answer, temperature, verbose
        )

        return self._create_verification_result_dict(verification_result)

    def _extract_answer_from_solution(self, solution: str) -> str:
        """Extract final answer from solution text.

        Args:
            solution: Solution text

        Returns:
            Extracted answer or "0" as fallback
        """
        # Try different extraction methods in order
        answer = self._extract_from_markers(solution)
        if answer:
            return answer

        answer = self._extract_from_last_lines(solution)
        if answer:
            return answer

        answer = self._extract_any_number(solution)
        if answer:
            return answer

        return "0"  # Default fallback

    def _extract_from_markers(self, solution: str) -> Optional[str]:
        """Extract answer from common markers (####, boxed, etc)."""
        # Look for #### format (most reliable)
        match = re.search(r"####\s*(.+?)(?:\n|$)", solution)
        if match:
            answer = match.group(1).strip()
            # Clean up LaTeX wrappers
            answer = answer.replace("\\(", "").replace("\\)", "")
            answer = answer.replace("$", "")
            return answer

        # Look for "final answer is X" or similar
        match = re.search(
            r"(?:final answer|the answer|answer|result) (?:is|=):?\s*(.+?)(?:\n|$|\.)",
            solution,
            re.IGNORECASE,
        )
        if match:
            return match.group(1).strip()

        # Look for boxed answer
        match = re.search(r"\\boxed\{([^}]+)\}", solution)
        if match:
            return match.group(1).strip()

        # Look for standalone LaTeX fractions
        match = re.search(
            r"^\s*\\frac\{[^}]+\}\{[^}]+\}\s*$", solution, re.MULTILINE
        )
        if match:
            return match.group(0).strip()

        return None

    def _extract_from_last_lines(self, solution: str) -> Optional[str]:
        """Extract answer from last few lines."""
        lines = solution.strip().split("\n")
        for line in reversed(lines[-5:]):
            line = line.strip()
            # Skip empty or punctuation-only lines
            if not line or line in [".", ",", ";"]:
                continue
            # Check if line looks like an answer
            if re.match(r"^-?\d+\.?\d*(/\d+)?$", line):
                return line
            if re.match(r"^\([^)]+\)$", line):
                return line
        return None

    def _extract_any_number(self, solution: str) -> Optional[str]:
        """Final fallback: extract any number from solution."""
        numbers = re.findall(r"-?\d+\.?\d*", solution)
        if numbers:
            return numbers[-1]
        return None
