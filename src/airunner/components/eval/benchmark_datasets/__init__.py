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

    Args:
        answer: Answer string

    Returns:
        Normalized answer (lowercase, stripped, no punctuation)
    """
    # Simple normalization only - NO manual LaTeX conversion
    # LaTeX conversion is now handled by LLM tool convert_to_latex()

    # Normalize LaTeX fractions: \frac{a}{b} -> a/b
    # This handles the common case where model uses \frac but expected uses /
    import re

    answer = re.sub(r"\\frac\{([^}]+)\}\{([^}]+)\}", r"\1/\2", answer)

    # Normalize LaTeX line breaks in matrices (\\  or \\ both become single space)
    answer = re.sub(r"\\\\\s*", " ", answer)

    # Normalize LaTeX spacing commands
    answer = answer.replace(r"\,", "")  # Thin space
    answer = answer.replace(r"\ ", " ")  # Normal space

    # Normalize whitespace (collapse multiple spaces to single space)
    answer = re.sub(r"\s+", " ", answer)

    # Remove commas from numbers
    answer = answer.replace(",", "")
    # Lowercase
    answer = answer.lower().strip()
    # Remove trailing periods
    answer = answer.rstrip(".")
    # Remove dollar signs, percent signs
    answer = answer.replace("$", "").replace("%", "")
    return answer
