"""
Standard benchmark datasets for evaluation.

Provides loaders for industry-standard datasets:
- GSM8K: Grade school math problems
- MATH: Competition-level math problems
- HumanEval: Code generation benchmark

Uses Hugging Face datasets library for easy access.
"""

import re
from typing import Optional
import logging


logger = logging.getLogger(__name__)


def extract_numeric_answer(text: str) -> Optional[str]:
    """Extract numeric answer from text.

    Looks for patterns like:
    - "\\boxed{42}" (MATH dataset format, handles nested braces)
    - "#### 42" (GSM8K format)
    - "The answer is 42"
    - "= 42" at end
    - Final number in text

    Args:
        text: Text containing answer

    Returns:
        Extracted numeric answer or None
    """
    # MATH dataset format: \boxed{answer} with nested brace handling
    # Look for ALL boxed answers and take the LAST one (final answer)
    boxed_answers = []
    pos = 0
    while True:
        boxed_pos = text.find(r"\boxed{", pos)
        if boxed_pos == -1:
            break
        start = boxed_pos + len(r"\boxed{")
        brace_count = 1
        i = start
        while i < len(text) and brace_count > 0:
            if text[i] == "{":
                brace_count += 1
            elif text[i] == "}":
                brace_count -= 1
            i += 1
        if brace_count == 0:
            boxed_answers.append(text[start : i - 1].strip())
        pos = boxed_pos + 1

    if boxed_answers:
        return boxed_answers[-1]  # Return LAST boxed answer

    # Also check for matrix/vector format without \boxed:
    # \begin{pmatrix} ... \end{pmatrix} or \begin{bmatrix} ... \end{bmatrix}
    # Find ALL matrices and take the LAST one (final answer)
    matrix_matches = re.findall(
        r"\\begin\{[pb]matrix\}.+?\\end\{[pb]matrix\}", text, re.DOTALL
    )
    if matrix_matches:
        # Return the LAST matrix including the begin/end tags for proper comparison
        return matrix_matches[-1].strip()

    # GSM8K format: #### answer
    gsm8k_match = re.search(r"####\s*(.+?)(?:\n|$)", text)
    if gsm8k_match:
        answer = gsm8k_match.group(1).strip()
        # Clean up LaTeX wrappers
        answer = answer.replace("\\(", "").replace("\\)", "")
        answer = answer.replace("$", "")
        return answer

    # "The answer is X" format (find last occurrence)
    # Also look for "the smallest/largest/minimum/maximum is X"
    matches = list(
        re.finditer(
            r"(?:the answer is|answer:|smallest.*is|largest.*is|minimum.*is|maximum.*is|thus,?|therefore,?)\s+(?:\\\[)?([^,\n\.]+?)(?:\\\])?(?:\n|$|\.|\,)",
            text,
            re.IGNORECASE,
        )
    )
    if matches:
        # Take last match
        answer = matches[-1].group(1).strip()
        answer = answer.replace(",", "").replace("$", "")
        # Clean up common LaTeX wrappers
        answer = answer.replace("\\(", "").replace("\\)", "")
        return answer

    # "= X" format at end of line (find last occurrence near end)
    lines = text.split("\n")
    for line in reversed(lines[-10:]):  # Check last 10 lines
        equals_match = re.search(r"=\s*([^\s]+)", line)
        if equals_match:
            answer = equals_match.group(1).strip()
            answer = answer.replace(",", "").replace("$", "")
            # Avoid extracting equation numbers or intermediate steps
            if not answer.startswith("(") and answer not in ["0", "1"]:
                return answer

    # Last number in text (fallback)
    numbers = re.findall(r"-?[\d,]+\.?\d*", text)
    if numbers:
        return numbers[-1].replace(",", "")

    return None


def normalize_answer(answer: str) -> str:
    """Normalize answer for comparison.

    Handles LaTeX formatting differences, whitespace, and common mathematical
    notations to determine if two answers are mathematically equivalent.

    Args:
        answer: Answer string

    Returns:
        Normalized answer (lowercase, stripped, standardized formatting)
    """
    import re

    # Normalize LaTeX spacing commands FIRST (before whitespace processing)
    answer = answer.replace(r"\,", "")  # Thin space
    answer = answer.replace(r"\ ", " ")  # Normal space
    answer = answer.replace(r"\;", "")  # Medium space
    answer = answer.replace(r"\:", "")  # Medium space
    answer = answer.replace(r"\!", "")  # Negative thin space

    # Normalize whitespace (collapse multiple spaces to single space, remove ALL spaces)
    # This handles "2\pi" vs "2 \pi" by making both "2\pi"
    answer = re.sub(r"\s+", "", answer)

    # Normalize LaTeX line breaks in matrices
    answer = re.sub(r"\\\\\s*", "", answer)

    # Remove commas from numbers
    answer = answer.replace(",", "")

    # Lowercase
    answer = answer.lower().strip()

    # Remove trailing periods
    answer = answer.rstrip(".")

    # Remove dollar signs, percent signs
    answer = answer.replace("$", "").replace("%", "")

    # Normalize pi notation: π -> pi
    answer = answer.replace("π", "pi")

    # Normalize multiplication symbols
    answer = answer.replace(r"\cdot", "*")
    answer = answer.replace(r"\times", "*")

    # Normalize division: ÷ -> /
    answer = answer.replace("÷", "/")

    # Final cleanup
    answer = answer.strip()
    return answer


def answers_are_equivalent(answer1: str, answer2: str) -> bool:
    """Check if two answers are mathematically equivalent.

    Uses multiple strategies:
    1. Exact match after normalization
    2. Numerical comparison (if both are numbers)
    3. Symbolic comparison using sympy (if available)

    Args:
        answer1: First answer
        answer2: Second answer

    Returns:
        True if answers are mathematically equivalent
    """
    if not answer1 or not answer2:
        return False

    # Strategy 1: Exact match after normalization
    norm1 = normalize_answer(answer1)
    norm2 = normalize_answer(answer2)

    if norm1 == norm2:
        return True

    # Strategy 2: Numerical comparison (handle floating point precision)
    try:
        # Try to parse as numbers
        num1 = float(norm1)
        num2 = float(norm2)
        # Use relative tolerance for comparison
        return (
            abs(num1 - num2) < 1e-6
            or abs(num1 - num2) / max(abs(num1), abs(num2)) < 1e-6
        )
    except (ValueError, ZeroDivisionError):
        pass

    # Strategy 3: Symbolic math comparison using sympy
    try:
        import sympy as sp

        def latex_to_sympy(text: str) -> sp.Expr:
            """Convert LaTeX to sympy expression using built-in parser."""
            # Use sympy's built-in LaTeX parser
            from sympy.parsing.latex import parse_latex

            try:
                # Try using sympy's LaTeX parser first
                expr = parse_latex(text)
                # Expand and simplify to normalize form
                return sp.expand(sp.simplify(expr))
            except Exception:
                # Fallback to manual conversion for simple cases
                # Remove spaces
                text = text.replace(" ", "")
                # Replace LaTeX commands with sympy equivalents
                text = text.replace(r"\pi", "pi")
                text = text.replace("π", "pi")
                # Use sympify which can handle basic math notation
                expr = sp.sympify(text)
                return sp.expand(sp.simplify(expr))

        expr1 = latex_to_sympy(answer1)
        expr2 = latex_to_sympy(answer2)

        # Check if expressions are equivalent using multiple methods
        # Method 1: Direct equality after simplification
        if expr1 == expr2:
            return True

        # Method 2: Check if difference simplifies to zero
        diff = sp.simplify(expr1 - expr2)
        if diff == 0:
            return True

        # Method 3: Expand both and compare
        if sp.expand(expr1) == sp.expand(expr2):
            return True

        return False

    except Exception as e:
        # If sympy fails, fall back to string comparison
        logger.debug(f"Sympy comparison failed: {e}")
        pass

    # No match found
    return False
