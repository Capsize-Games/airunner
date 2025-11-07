"""
Multi-method answer evaluation for math problems.

Combines multiple evaluation strategies to produce a comprehensive score.
"""

import re
import math
from fractions import Fraction
from typing import Optional, Tuple, Dict, Any, List
from airunner.components.eval.benchmark_datasets import normalize_answer
from airunner.settings import AIRUNNER_LOG_LEVEL
from airunner.utils.application import get_logger

logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)


def _convert_unicode_to_latex(s: str) -> str:
    """Convert Unicode math symbols to LaTeX equivalents.

    Args:
        s: String potentially containing Unicode math symbols

    Returns:
        String with Unicode converted to LaTeX
    """
    unicode_to_latex = {
        "√": "\\sqrt",
        "π": "\\pi",
        "±": "\\pm",
    }
    for unicode_char, latex_cmd in unicode_to_latex.items():
        if unicode_char == "√":
            s = re.sub(r"√\(([^)]+)\)", r"\\sqrt{\1}", s)
            s = re.sub(r"√(\w+)", r"\\sqrt{\1}", s)
        else:
            s = s.replace(unicode_char, latex_cmd)
    return s


def _eval_latex_expression(
    s: str, is_negative: bool = False
) -> Optional[float]:
    """Evaluate LaTeX expression by converting to Python.

    Args:
        s: LaTeX string
        is_negative: Whether to negate result

    Returns:
        Numeric result or None
    """
    try:
        expr = re.sub(r"\\sqrt\{([^}]+)\}", r"math.sqrt(\1)", s)
        expr = re.sub(r"\\frac\{([^}]+)\}\{([^}]+)\}", r"((\1)/(\2))", expr)
        expr = expr.replace("\\", "")

        if all(c in "0123456789.+-*/()\nsqrtmath." for c in expr):
            result = eval(expr, {"__builtins__": {}, "math": math})
            return -result if is_negative else float(result)
    except:
        pass
    return None


def _parse_latex_fraction(
    s: str, is_negative: bool = False
) -> Optional[float]:
    """Parse LaTeX fraction \\frac{a}{b}.

    Args:
        s: String containing fraction
        is_negative: Whether to negate result

    Returns:
        Numeric result or None
    """
    frac_match = re.search(r"\\frac\{([^}]+)\}\{([^}]+)\}", s)
    if frac_match:
        try:
            numerator = parse_latex_to_number(frac_match.group(1))
            denominator = parse_latex_to_number(frac_match.group(2))
            if (
                numerator is not None
                and denominator is not None
                and denominator != 0
            ):
                result = numerator / denominator
                return -result if is_negative else result
        except (ValueError, ZeroDivisionError):
            pass
    return None


def _parse_latex_sqrt(s: str, is_negative: bool = False) -> Optional[float]:
    """Parse LaTeX square root \\sqrt{a}.

    Args:
        s: String containing sqrt
        is_negative: Whether to negate result

    Returns:
        Numeric result or None
    """
    sqrt_match = re.search(r"\\sqrt\{([^}]+)\}", s)
    if sqrt_match:
        try:
            inner = parse_latex_to_number(sqrt_match.group(1))
            if inner is not None and inner >= 0:
                result = math.sqrt(inner)
                return -result if is_negative else result
        except ValueError:
            pass
    return None


def parse_latex_to_number(latex_str: str) -> Optional[float]:
    """Parse LaTeX mathematical expressions to numeric values.

    Args:
        latex_str: LaTeX expression like \\frac{3}{8}, \\sqrt{3}, etc.

    Returns:
        Numeric value or None if cannot parse
    """
    if not latex_str:
        return None

    # Normalize and clean
    s = latex_str.strip()
    s = _convert_unicode_to_latex(s)
    s = s.replace("$", "").replace(" ", "")

    # Handle complex expressions with operators
    if _has_operators(s):
        result = _eval_latex_expression(s)
        if result is not None:
            return result

    # Handle negative sign
    is_negative, s = _extract_sign(s)

    # Try parsing specific patterns
    return _try_parse_patterns(s, is_negative)


def _has_operators(s: str) -> bool:
    """Check if string has mathematical operators."""
    return any(op in s[1:] for op in ["+", "-"]) and (
        "\\frac" in s or "\\sqrt" in s
    )


def _extract_sign(s: str) -> Tuple[bool, str]:
    """Extract negative sign from string."""
    is_negative = s.startswith("-")
    if is_negative:
        s = s[1:]
    return is_negative, s


def _try_parse_patterns(s: str, is_negative: bool) -> Optional[float]:
    """Try parsing different LaTeX patterns."""
    # Try fraction
    result = _parse_latex_fraction(s, is_negative)
    if result is not None:
        return result

    # Try sqrt
    result = _parse_latex_sqrt(s, is_negative)
    if result is not None:
        return result

    # Try eval
    result = _eval_latex_expression(s, is_negative)
    if result is not None:
        return result

    # Try direct float conversion
    try:
        result = float(s)
        return -result if is_negative else result
    except ValueError:
        pass

    return None


def parse_answer_to_number(answer: Any) -> Optional[float]:
    """Parse various answer formats to a numeric value.

    Args:
        answer: Answer in various formats (string, number, list, etc.)

    Returns:
        Numeric value or None
    """
    if answer is None:
        return None

    # Already a number
    if isinstance(answer, (int, float)):
        return float(answer)

    # List/tuple - try first element
    if isinstance(answer, (list, tuple)) and len(answer) > 0:
        return parse_answer_to_number(answer[0])

    # String - try various parsers
    if isinstance(answer, str):
        return _parse_answer_string(answer)

    return None


def _parse_answer_string(answer: str) -> Optional[float]:
    """Parse answer string to number."""
    # Try LaTeX parser first
    latex_num = parse_latex_to_number(answer)
    if latex_num is not None:
        return latex_num

    # Try exact fraction string like '3/8'
    frac_num = _try_parse_fraction_string(answer)
    if frac_num is not None:
        return frac_num

    # Try direct conversion
    try:
        return float(answer)
    except ValueError:
        pass

    # Try extracting first number
    numbers = re.findall(r"-?\d+\.?\d*", answer)
    if numbers:
        try:
            return float(numbers[0])
        except ValueError:
            pass

    return None


def _try_parse_fraction_string(answer: str) -> Optional[float]:
    """Try to parse fraction string like '3/8'."""
    frac_match = re.match(r"^\s*(-?\d+)\s*/\s*(\d+)\s*$", answer)
    if frac_match:
        try:
            return float(
                Fraction(int(frac_match.group(1)), int(frac_match.group(2)))
            )
        except Exception:
            pass
    return None


def try_fraction(x: Any) -> Optional[Fraction]:
    """Convert value to Fraction if possible.

    Args:
        x: Value to convert (int, float, str, Fraction)

    Returns:
        Fraction or None
    """
    if x is None:
        return None
    if isinstance(x, (int,)):
        return Fraction(int(x), 1)
    if isinstance(x, Fraction):
        return x
    if isinstance(x, float):
        return _float_to_fraction(x)
    if isinstance(x, str):
        return _string_to_fraction(x)
    return None


def _float_to_fraction(x: float) -> Optional[Fraction]:
    """Convert float to Fraction."""
    try:
        return Fraction(x).limit_denominator(1000000)
    except Exception:
        return None


def _string_to_fraction(x: str) -> Optional[Fraction]:
    """Convert string to Fraction."""
    # Try simple fraction "a/b"
    m = re.match(r"^\s*(-?\d+)\s*/\s*(\d+)\s*$", x)
    if m:
        try:
            return Fraction(int(m.group(1)), int(m.group(2)))
        except Exception:
            return None

    # Try LaTeX fraction \frac{a}{b}
    m2 = re.search(r"\\frac\{\s*([^}]+)\s*\}\{\s*([^}]+)\s*\}", x)
    if m2:
        try:
            num = parse_answer_to_number(m2.group(1))
            den = parse_answer_to_number(m2.group(2))
            if num is not None and den is not None:
                return Fraction(
                    Fraction(num).limit_denominator(1000000)
                ) / Fraction(Fraction(den).limit_denominator(1000000))
        except Exception:
            pass
    return None


def _compute_match_score(
    ans_f: float, exp_f: float, tolerance: float = 1e-3
) -> Tuple[bool, float]:
    """Compute match score based on tolerance.

    Args:
        ans_f: Answer value
        exp_f: Expected value
        tolerance: Acceptable difference

    Returns:
        (is_match, score)
    """
    # Near-zero: use absolute tolerance
    if abs(exp_f) < 1e-12:
        diff = abs(ans_f - exp_f)
        if diff <= tolerance:
            score = max(0.0, 1.0 - (diff / tolerance))
            return True, score
        return False, 0.0

    # Non-zero: use relative error
    relative_error = abs(ans_f - exp_f) / abs(exp_f)
    if relative_error <= tolerance:
        score = max(0.0, 1.0 - (relative_error / tolerance))
        return True, score

    return False, 0.0


def compare_numeric_answers(
    answer: Any, expected: Any, tolerance: float = 1e-3
) -> Tuple[bool, float]:
    """Compare two answers numerically with tolerance.

    Args:
        answer: Computed answer
        expected: Expected answer
        tolerance: Acceptable difference (default 0.001 = 0.1%)

    Returns:
        (is_match, confidence_score)
    """
    # Try exact rational comparison first
    ans_frac = try_fraction(answer)
    exp_frac = try_fraction(expected)

    if ans_frac is not None and exp_frac is not None:
        if ans_frac == exp_frac:
            return True, 1.0
        ans_f = float(ans_frac)
        exp_f = float(exp_frac)
    else:
        ans_f = parse_answer_to_number(answer)
        exp_f = parse_answer_to_number(expected)

    if ans_f is None or exp_f is None:
        return False, 0.0

    return _compute_match_score(ans_f, exp_f, tolerance)


def _is_tuple_like(s: Any) -> bool:
    """Check if value looks like a tuple/vector.

    Handles: (a,b,c), \\left(a,b,c\\right), [a,b,c], \\begin{pmatrix}...\\end{pmatrix}, etc.
    """
    if isinstance(s, (list, tuple)):
        return True
    if not isinstance(s, str):
        return False
    s = s.strip()
    # Check for pmatrix format
    if r"\begin{pmatrix}" in s or "\\begin{pmatrix}" in s:
        return True
    # Remove LaTeX \left and \right wrappers
    s = s.replace(r"\left", "").replace(r"\right", "")
    s = s.strip()
    return (s.startswith("(") and s.endswith(")")) or (
        s.startswith("[") and s.endswith("]")
    )


def _parse_pmatrix(s: str) -> Optional[List[float]]:
    """Parse LaTeX pmatrix format.

    Args:
        s: String potentially containing pmatrix

    Returns:
        List of floats or None
    """
    pmatrix_match = re.search(
        r"\\begin\{pmatrix\}(.+?)\\end\{pmatrix\}", s, re.DOTALL
    )
    if pmatrix_match:
        content = pmatrix_match.group(1).strip()
        parts = re.split(r"\\\\\s*", content)
        parts = [p.strip() for p in parts if p.strip()]
        nums = []
        for p in parts:
            v = parse_answer_to_number(p)
            if v is None:
                return None
            nums.append(v)
        return nums if nums else None
    return None


def _smart_split_tuple(inner: str) -> List[str]:
    """Split tuple elements respecting nested braces.

    Args:
        inner: Inner content of tuple (without parentheses)

    Returns:
        List of element strings
    """
    parts = []
    current = ""
    depth = 0
    for char in inner:
        if char == "{":
            depth += 1
            current += char
        elif char == "}":
            depth -= 1
            current += char
        elif char == "," and depth == 0:
            parts.append(current.strip())
            current = ""
        else:
            current += char
    if current.strip():
        parts.append(current.strip())
    return parts


def _parse_tuple(s: Any) -> Optional[List[float]]:
    """Parse tuple/vector to list of floats.

    Handles LaTeX tuples like \\left(\\frac{1}{2}, \\sqrt{3}, 0\\right) and pmatrix
    """
    # Handle list/tuple directly
    if isinstance(s, (list, tuple)):
        return _parse_list_elements(s)

    if isinstance(s, str):
        return _parse_tuple_string(s)

    return None


def _parse_list_elements(items: Any) -> Optional[List[float]]:
    """Parse elements from list/tuple."""
    nums = []
    for item in items:
        v = parse_answer_to_number(item)
        if v is None:
            return None
        nums.append(v)
    return nums


def _parse_tuple_string(s: str) -> Optional[List[float]]:
    """Parse tuple from string."""
    s2 = s.strip()

    # Try pmatrix format first
    result = _parse_pmatrix(s2)
    if result is not None:
        return result

    # Remove LaTeX wrappers
    s2 = s2.replace(r"\left", "").replace(r"\right", "").strip()

    # Handle parentheses or brackets
    if (s2.startswith("(") and s2.endswith(")")) or (
        s2.startswith("[") and s2.endswith("]")
    ):
        inner = s2[1:-1]
        parts = _smart_split_tuple(inner)
        return _parse_tuple_parts(parts)

    return None


def _parse_tuple_parts(parts: List[str]) -> Optional[List[float]]:
    """Parse individual tuple parts to numbers."""
    nums = []
    for p in parts:
        v = parse_answer_to_number(p)
        if v is None:
            return None
        nums.append(v)
    return nums


def _evaluate_exact_match(answer: Any, expected: Any) -> Dict[str, Any]:
    """Evaluate using exact string match.

    Args:
        answer: Computed answer
        expected: Expected answer

    Returns:
        Dict with score and match status
    """
    if answer and expected:
        norm_answer = normalize_answer(str(answer))
        norm_expected = normalize_answer(str(expected))
        exact_match = norm_answer == norm_expected
        return {"score": 1.0 if exact_match else 0.0, "matched": exact_match}
    return {"score": 0.0, "matched": False}


def _evaluate_tuple_comparison(
    answer: Any, expected: Any
) -> tuple[bool, float, Any, Any]:
    """Compare tuple-like answers element by element.

    Returns:
        Tuple of (match, score, parsed_answer, parsed_expected)
    """
    ans_list = _parse_tuple(answer)
    exp_list = _parse_tuple(expected)

    if (
        ans_list is not None
        and exp_list is not None
        and len(ans_list) == len(exp_list)
    ):
        return _compare_tuple_elements(ans_list, exp_list)

    # Fall back to simple comparison
    match, score = compare_numeric_answers(answer, expected)
    return (
        match,
        score,
        parse_answer_to_number(answer),
        parse_answer_to_number(expected),
    )


def _compare_tuple_elements(
    ans_list: List[float], exp_list: List[float]
) -> tuple[bool, float, List[float], List[float]]:
    """Compare tuple elements pairwise."""
    elem_scores = []
    elem_matches = []
    for a_elem, e_elem in zip(ans_list, exp_list):
        match, score = compare_numeric_answers(a_elem, e_elem)
        elem_scores.append(score)
        elem_matches.append(match)

    numeric_score = sum(elem_scores) / len(elem_scores)
    numeric_match = all(elem_matches)
    return numeric_match, numeric_score, ans_list, exp_list


def _evaluate_numeric(answer: Any, expected: Any) -> Dict[str, Any]:
    """Evaluate using numeric comparison.

    Args:
        answer: Computed answer
        expected: Expected answer

    Returns:
        Dict with score, match status, and parsed values
    """
    if _is_tuple_like(answer) and _is_tuple_like(expected):
        (
            numeric_match,
            numeric_score,
            parsed_answer_val,
            parsed_expected_val,
        ) = _evaluate_tuple_comparison(answer, expected)
    else:
        numeric_match, numeric_score = compare_numeric_answers(
            answer, expected
        )
        parsed_answer_val = parse_answer_to_number(answer)
        parsed_expected_val = parse_answer_to_number(expected)

    return {
        "score": numeric_score,
        "matched": numeric_match,
        "parsed_answer": parsed_answer_val,
        "parsed_expected": parsed_expected_val,
    }


def _evaluate_latex(answer: Any, expected: Any) -> Dict[str, Any]:
    """Evaluate using LaTeX parsing.

    Args:
        answer: Computed answer
        expected: Expected answer

    Returns:
        Dict with score, match status, and parsed values
    """
    latex_answer = parse_latex_to_number(str(answer)) if answer else None
    latex_expected = parse_latex_to_number(str(expected)) if expected else None
    latex_match = False
    latex_score = 0.0

    if latex_answer is not None and latex_expected is not None:
        latex_diff = abs(latex_answer - latex_expected)
        if abs(latex_expected) > 1e-10:
            latex_rel_error = latex_diff / abs(latex_expected)
            latex_match = latex_rel_error < 1e-3
            latex_score = (
                1.0 - min(1.0, latex_rel_error / 1e-3) if latex_match else 0.0
            )
        else:
            latex_match = latex_diff < 1e-3
            latex_score = 1.0 if latex_match else 0.0

    return {
        "score": latex_score,
        "matched": latex_match,
        "parsed_answer": latex_answer,
        "parsed_expected": latex_expected,
    }


def _evaluate_llm_judge(
    evaluator_func: Optional[callable],
    question: str,
    solution_text: str,
    reference_solution: str,
) -> Dict[str, Any]:
    """Evaluate using LLM as judge.

    Args:
        evaluator_func: Optional evaluator function
        question: Original question
        solution_text: Full solution text
        reference_solution: Reference solution

    Returns:
        Dict with score and optional reasoning
    """
    if not evaluator_func or not question:
        return {"score": 0.0, "skipped": True}

    try:
        eval_result = evaluator_func(
            inputs=question,
            outputs=solution_text,
            reference_outputs=reference_solution,
        )
        return {
            "score": eval_result.get("score", 0.0),
            "reasoning": eval_result.get("reasoning", ""),
        }
    except Exception as e:
        logger.warning(f"LLM evaluator failed: {e}")
        return {"score": 0.0, "error": str(e)}


def multi_method_evaluate(
    answer: Any,
    expected: Any,
    solution_text: str,
    reference_solution: str,
    evaluator_func: Optional[callable] = None,
    question: str = "",
) -> Dict[str, Any]:
    """Evaluate answer using multiple methods and combine scores.

    Args:
        answer: Computed answer
        expected: Expected answer
        solution_text: Full solution text from LLM
        reference_solution: Reference solution text
        evaluator_func: Optional LLM-as-judge evaluator
        question: Original question (for evaluator)

    Returns:
        Dict with scores, methods, and final combined score
    """
    results = _initialize_results(answer, expected)
    _run_evaluation_methods(
        results,
        answer,
        expected,
        evaluator_func,
        question,
        solution_text,
        reference_solution,
    )
    _compute_final_score(results)
    return results


def _initialize_results(answer: Any, expected: Any) -> Dict[str, Any]:
    """Initialize results dictionary."""
    return {
        "answer": answer,
        "expected": expected,
        "methods": {},
        "final_score": 0.0,
        "is_correct": False,
    }


def _run_evaluation_methods(
    results: Dict,
    answer: Any,
    expected: Any,
    evaluator_func: Optional[callable],
    question: str,
    solution_text: str,
    reference_solution: str,
) -> None:
    """Run all evaluation methods and store results."""
    results["methods"]["exact_match"] = _evaluate_exact_match(answer, expected)
    results["methods"]["numeric"] = _evaluate_numeric(answer, expected)
    results["methods"]["latex"] = _evaluate_latex(answer, expected)
    results["methods"]["llm_judge"] = _evaluate_llm_judge(
        evaluator_func, question, solution_text, reference_solution
    )


def _compute_final_score(results: Dict) -> None:
    """Compute final weighted score and correctness."""
    weights = {
        "exact_match": 0.10,
        "numeric": 0.45,
        "latex": 0.35,
        "llm_judge": 0.10,
    }

    total_score = sum(
        results["methods"][method]["score"] * weight
        for method, weight in weights.items()
        if method in results["methods"]
    )

    results["final_score"] = total_score
    results["is_correct"] = total_score >= 0.44
