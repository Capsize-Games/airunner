"""Self-verification solver for math problem accuracy."""

import re
from typing import Any, Dict, Optional, Tuple

from airunner_services.settings import AIRUNNER_LOG_LEVEL
from airunner_services.utils.application import get_logger
from airunner_services.eval.math_tools._executor import SafePythonExecutor

logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)


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
        except Exception:
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
