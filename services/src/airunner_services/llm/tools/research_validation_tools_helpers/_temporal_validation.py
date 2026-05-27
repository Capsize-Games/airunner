"""Temporal validation helpers for research tools."""

import re
from datetime import datetime


def extract_age_from_text_impl(content: str) -> dict:
    """Extract approximate age from text content."""
    if not content:
        return _missing_age_result()
    text = f" {content.lower()} "
    age_match = _explicit_age_result(text)
    if age_match is not None:
        return age_match
    birth_year_match = _birth_year_result(text)
    if birth_year_match is not None:
        return birth_year_match
    return _missing_age_result()


def get_current_date_context_impl() -> dict:
    """Return the current date information used in research validation."""
    now = datetime.now()
    return {
        "date_full": now.strftime("%B %d, %Y"),
        "date_iso": now.strftime("%Y-%m-%d"),
        "year": now.year,
        "month": now.month,
        "day": now.day,
        "timestamp": now.strftime("%Y-%m-%d %H:%M:%S"),
    }


def check_temporal_accuracy_impl(
    content: str,
    subject_context: str = "",
) -> dict:
    """Check content for temporal accuracy issues."""
    current_date = datetime.now()
    current_year = current_date.year
    content_lower = content.lower()
    issues = _former_position_issues(content_lower)
    issues.extend(_future_year_issues(content, content_lower, current_year))
    issues.extend(_death_year_issues(content_lower, current_year))
    suggestions = _date_consistency_suggestions(content)
    suggestions.extend(_subject_context_suggestions(subject_context, content_lower))
    return {
        "issues_found": bool(issues),
        "issues": issues,
        "suggestions": suggestions,
        "current_date": current_date.strftime("%B %d, %Y"),
        "current_year": current_year,
    }


def _missing_age_result() -> dict:
    """Return the default age extraction payload."""
    return {"found": False, "age": None, "source_pattern": None}


def _explicit_age_result(text: str) -> dict | None:
    """Return an age payload when explicit age text is present."""
    year_old = re.search(r"(\d{1,3})\s*-?\s*years?\s*-?\s*old", text)
    if year_old is not None:
        return {"found": True, "age": int(year_old.group(1)), "source_pattern": "X-year-old"}
    age_match = re.search(r"age\s*(\d{1,3})", text)
    if age_match is not None:
        return {"found": True, "age": int(age_match.group(1)), "source_pattern": "age X"}
    return None


def _birth_year_result(text: str) -> dict | None:
    """Return an age payload derived from a detected birth year."""
    born_match = re.search(r"born\s*(?:in\s*)?(\d{4})", text)
    if born_match is None:
        return None
    year = int(born_match.group(1))
    approx_age = datetime.now().year - year
    if 0 < approx_age < 150:
        return {"found": True, "age": approx_age, "source_pattern": f"born in {year}"}
    return None


def _former_position_issues(content_lower: str) -> list[str]:
    """Return issues for former-title phrasing that needs review."""
    if "former" not in content_lower:
        return []
    issues: list[str] = []
    pattern = r"former\s+(\w+(?:\s+\w+)?)\s+(\w+(?:\s+\w+)?)"
    for match in re.finditer(pattern, content_lower):
        issues.append(
            f"Found 'former {match.group(1)}' - verify this is accurate for the timeframe"
        )
    return issues


def _future_year_issues(
    content: str,
    content_lower: str,
    current_year: int,
) -> list[str]:
    """Return issues for future years that may be framed as past events."""
    issues: list[str] = []
    year_pattern = r"\b(20[3-9]\d|2[1-9]\d{2})\b"
    for year in set(re.findall(year_pattern, content)):
        if int(year) > current_year and re.search(rf"(?:in|during|since)\s+{year}", content_lower):
            issues.append(f"Year {year} is in the future but may be referenced as past")
    return issues


def _death_year_issues(content_lower: str, current_year: int) -> list[str]:
    """Return issues for impossible future death years."""
    if "died" not in content_lower and "death" not in content_lower:
        return []
    match = re.search(
        r"died\s+(?:in\s+)?(\d{4})|death\s+(?:in\s+)?(\d{4})",
        content_lower,
    )
    if match is None:
        return []
    death_year = int(match.group(1) or match.group(2))
    if death_year > current_year:
        return [f"Death year {death_year} is in the future - verify accuracy"]
    return []


def _date_consistency_suggestions(content: str) -> list[str]:
    """Return suggestions when multiple dates appear in the content."""
    patterns = [
        r"(\d{1,2})[/\-](\d{1,2})[/\-](\d{2,4})",
        r"(\w+)\s+(\d{1,2}),?\s+(\d{4})",
    ]
    dates_found: list[tuple[str, ...]] = []
    for pattern in patterns:
        dates_found.extend(re.findall(pattern, content))
    if len(dates_found) > 1:
        return [f"Multiple dates found ({len(dates_found)}) - verify consistency"]
    return []


def _subject_context_suggestions(
    subject_context: str,
    content_lower: str,
) -> list[str]:
    """Return subject-specific temporal review suggestions."""
    context_lower = subject_context.lower()
    if "current" in context_lower and "former" in content_lower:
        return ["Subject context says 'current' but content uses 'former' - verify"]
    return []