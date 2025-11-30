"""
Research validation tools.

Provides tools for validating URLs, content quality, and fact-checking
research materials. These tools help ensure research quality by filtering
out low-quality sources, detecting malicious content, and validating
temporal accuracy.
"""

import re
from datetime import datetime
from typing import Annotated, Any, Optional
from urllib.parse import urlparse

from airunner.components.llm.core.tool_registry import tool, ToolCategory
from airunner.settings import AIRUNNER_LOG_LEVEL
from airunner.utils.application import get_logger

logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)


# Domain blacklist for sites that consistently block scraping
BLACKLISTED_DOMAINS = {
    "nytimes.com",
    "wsj.com",
    "ft.com",  # Financial Times
    "economist.com",
    "bloomberg.com",
    "bakerinstitute.org",  # Consistently returns 403
}

# Path segments that indicate irrelevant content
IRRELEVANT_PATH_SEGMENTS = [
    "/games/",
    "/game/",
    "/puzzle/",
    "/crossword/",
    "/sudoku/",
    "/login/",
    "/signin/",
    "/signup/",
    "/register/",
    "/account/",
    "/shop/",
    "/store/",
    "/product/",
    "/cart/",
    "/checkout/",
    "/jobs/",
    "/careers/",
    "/apply/",
    "/contact/",
    "/privacy/",
    "/terms/",
    "/help/",
    "/subscribe/",
    "/newsletter/",
    "/podcast/",
    "/video/",
    "/videos/",
    "/gallery/",
    "/photos/",
    "/events/",
    "/calendar/",
]

# Patterns that suggest prompt injection attempts
INJECTION_PATTERNS = [
    r"ignore (?:all )?previous instructions",
    r"ignore (?:all )?directions",
    r"forget (?:all )?previous instructions",
    r"system prompt:",
    r"you are now (?:a|an)",
    r"your new persona is",
    r"override (?:system|safety) (?:protocols|rules)",
    r"jailbreak mode",
    r"developer mode (?:on|enabled)",
    r"DAN mode",
    r"do anything now",
    r"repeat the following text forever",
    r"delete (?:all )?files",
    r"format your hard drive",
    r"install (?:malware|virus)",
]

# Hard block phrases indicating inaccessible content
HARD_BLOCK_PHRASES = [
    "request access",
    "access denied",
    "complete the captcha",
    "verify you are not a robot",
    "automated scraping",
    "404 not found",
    "page not found",
    "403 forbidden",
]


@tool(
    name="validate_url",
    category=ToolCategory.RESEARCH,
    description=(
        "Check if a URL is suitable for research scraping. "
        "Validates against blacklisted domains (paywalled sites), "
        "irrelevant path segments (games, login, shopping), and URL format. "
        "Use this BEFORE scraping to avoid wasting time on blocked sites."
    ),
    return_direct=False,
    requires_api=False,
)
def validate_url(
    url: Annotated[str, "The URL to validate"],
) -> dict:
    """Validate a URL for research scraping suitability.

    Checks:
    - Domain blacklist (paywalled sites that block scrapers)
    - Irrelevant path segments (login, games, shopping, etc.)
    - Basic URL format validity

    Args:
        url: URL to validate

    """
    try:
        parsed = urlparse(url)
        
        # Check basic format
        if not parsed.scheme or not parsed.netloc:
            return {
                "valid": False,
                "reason": "Invalid URL format - missing scheme or domain",
                "domain": None,
            }
        
        if parsed.scheme not in ("http", "https"):
            return {
                "valid": False,
                "reason": f"Unsupported URL scheme: {parsed.scheme}",
                "domain": None,
            }
        
        domain = parsed.netloc.lower()
        if domain.startswith("www."):
            domain = domain[4:]
        
        # Check domain blacklist
        for blacklisted in BLACKLISTED_DOMAINS:
            if domain == blacklisted or domain.endswith("." + blacklisted):
                return {
                    "valid": False,
                    "reason": f"Domain {domain} is blacklisted (typically paywalled or blocks scrapers)",
                    "domain": domain,
                }
        
        # Check irrelevant path segments
        path = parsed.path.lower()
        for segment in IRRELEVANT_PATH_SEGMENTS:
            if segment in path:
                return {
                    "valid": False,
                    "reason": f"URL contains irrelevant path segment: {segment.strip('/')}",
                    "domain": domain,
                }
        
        return {
            "valid": True,
            "reason": "URL is suitable for research scraping",
            "domain": domain,
        }
        
    except Exception as e:
        logger.error(f"URL validation error: {e}")
        return {
            "valid": False,
            "reason": f"Error validating URL: {str(e)}",
            "domain": None,
        }


@tool(
    name="validate_content",
    category=ToolCategory.RESEARCH,
    description=(
        "Validate scraped web content for quality and safety. "
        "Checks for: minimum length, blocked content indicators (CAPTCHA, 403), "
        "and potential prompt injection attempts. "
        "Use this AFTER scraping to filter out low-quality content."
    ),
    return_direct=False,
    requires_api=False,
)
def validate_content(
    content: Annotated[str, "The scraped content to validate"],
    source_url: Annotated[str, "The URL the content was scraped from"] = "",
) -> dict:
    """Validate scraped content quality and safety.

    Checks:
    - Minimum content length (200 chars)
    - Hard block indicators (CAPTCHA, 403/404 errors)
    - Prompt injection patterns

    Args:
        content: Scraped text content
        source_url: Source URL (for logging)

    """
    warnings = []
    
    # Check minimum length
    if not content or len(content) < 200:
        return {
            "valid": False,
            "reason": "Content too short (< 200 characters) - likely blocked or empty page",
            "warnings": warnings,
            "content_length": len(content) if content else 0,
        }
    
    content_lower = content.lower()
    
    # Check for hard block indicators
    for phrase in HARD_BLOCK_PHRASES:
        if phrase in content_lower[:2000]:  # Check beginning of content
            return {
                "valid": False,
                "reason": f"Content appears blocked: '{phrase}' detected",
                "warnings": warnings,
                "content_length": len(content),
            }
    
    # Check for prompt injection attempts
    scan_text = content[:5000] + "\n" + content[-5000:]
    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, scan_text, re.IGNORECASE):
            logger.warning(
                f"[Security] Blocked content from {source_url} - injection pattern: '{pattern}'"
            )
            return {
                "valid": False,
                "reason": f"Security: Potential prompt injection detected",
                "warnings": warnings,
                "content_length": len(content),
            }
    
    # Non-fatal warnings
    if "cookie" in content_lower[:1000] and "accept" in content_lower[:1000]:
        warnings.append("Page may have cookie consent banner")
    
    if "javascript" in content_lower[:500] and "enable" in content_lower[:500]:
        warnings.append("Page may require JavaScript for full content")
    
    return {
        "valid": True,
        "reason": "Content quality acceptable",
        "warnings": warnings,
        "content_length": len(content),
    }


@tool(
    name="extract_age_from_text",
    category=ToolCategory.RESEARCH,
    description=(
        "Extract approximate age from text content. "
        "Looks for patterns like '60-year-old', 'age 60', 'born in 1964'. "
        "Useful for validating content about the correct person."
    ),
    return_direct=False,
    requires_api=False,
)
def extract_age_from_text(
    content: Annotated[str, "Text content to search for age information"],
) -> dict:
    """Extract approximate age from text.

    Searches for age patterns and calculates age from birth year if found.

    Args:
        content: Text to search

    """
    if not content:
        return {"found": False, "age": None, "source_pattern": None}
    
    text = " " + content.lower() + " "
    
    # Pattern: "60-year-old" or "60 year old" or "60-year old"
    m = re.search(r"(\d{1,3})\s*-?\s*years?\s*-?\s*old", text)
    if m:
        return {
            "found": True,
            "age": int(m.group(1)),
            "source_pattern": "X-year-old",
        }
    
    # Pattern: "age 60"
    m = re.search(r"age\s*(\d{1,3})", text)
    if m:
        return {
            "found": True,
            "age": int(m.group(1)),
            "source_pattern": "age X",
        }
    
    # Pattern: "born in 1964" or "born 1964"
    m = re.search(r"born\s*(?:in\s*)?(\d{4})", text)
    if m:
        year = int(m.group(1))
        current_year = datetime.now().year
        approx_age = current_year - year
        if 0 < approx_age < 150:
            return {
                "found": True,
                "age": approx_age,
                "source_pattern": f"born in {year}",
            }
    
    return {"found": False, "age": None, "source_pattern": None}


@tool(
    name="get_current_date_context",
    category=ToolCategory.RESEARCH,
    description=(
        "Get the current date formatted for research context. "
        "Use this when fact-checking to ensure temporal accuracy - "
        "e.g., verifying someone is 'current' vs 'former' in a position."
    ),
    return_direct=False,
    requires_api=False,
)
def get_current_date_context() -> dict:
    """Get current date information for temporal validation.

    """
    now = datetime.now()
    return {
        "date_full": now.strftime("%B %d, %Y"),
        "date_iso": now.strftime("%Y-%m-%d"),
        "year": now.year,
        "month": now.month,
        "day": now.day,
        "timestamp": now.strftime("%Y-%m-%d %H:%M:%S"),
    }


@tool(
    name="check_temporal_accuracy",
    category=ToolCategory.RESEARCH,
    description=(
        "Check text for potential temporal/timeline errors. "
        "Detects issues like: calling current officials 'former', "
        "referring to future events as past, date inconsistencies. "
        "CRITICAL for research accuracy - use before finalizing reports."
    ),
    return_direct=False,
    requires_api=False,
)
def check_temporal_accuracy(
    content: Annotated[str, "Text content to check for temporal issues"],
    subject_context: Annotated[
        str,
        "Context about the subject (e.g., 'John Smith, current CEO of Acme Corp')"
    ] = "",
) -> dict:
    """Check content for temporal accuracy issues.

    Looks for potential timeline problems:
    - "Former" used for current positions
    - Future events described as past
    - Date inconsistencies
    - Anachronisms

    Args:
        content: Text to analyze
        subject_context: Optional context about the subject

    """
    issues = []
    suggestions = []
    current_year = datetime.now().year
    current_date = datetime.now()
    
    content_lower = content.lower()
    
    # Check for "former" with current year context
    if "former" in content_lower:
        # Look for patterns like "former X (position) Y (name)"
        former_matches = re.finditer(
            r"former\s+(\w+(?:\s+\w+)?)\s+(\w+(?:\s+\w+)?)",
            content_lower
        )
        for match in former_matches:
            position = match.group(1)
            # Flag for manual review
            issues.append(
                f"Found 'former {position}' - verify this is accurate for the timeframe"
            )
    
    # Check for future years mentioned as past
    year_pattern = r"\b(20[3-9]\d|2[1-9]\d{2})\b"  # Years 2030+ or 2100+
    future_years = re.findall(year_pattern, content)
    for year in set(future_years):
        year_int = int(year)
        if year_int > current_year:
            # Check context - is it mentioned as if it already happened?
            context_pattern = rf"(?:in|during|since)\s+{year}"
            if re.search(context_pattern, content_lower):
                issues.append(
                    f"Year {year} is in the future but may be referenced as past"
                )
    
    # Check for inconsistent dates
    date_patterns = [
        r"(\d{1,2})[/\-](\d{1,2})[/\-](\d{2,4})",  # MM/DD/YYYY or DD/MM/YYYY
        r"(\w+)\s+(\d{1,2}),?\s+(\d{4})",  # Month DD, YYYY
    ]
    
    dates_found = []
    for pattern in date_patterns:
        matches = re.findall(pattern, content)
        dates_found.extend(matches)
    
    if len(dates_found) > 1:
        suggestions.append(
            f"Multiple dates found ({len(dates_found)}) - verify consistency"
        )
    
    # Check for death dates that seem wrong
    if "died" in content_lower or "death" in content_lower:
        death_year_match = re.search(
            r"died\s+(?:in\s+)?(\d{4})|death\s+(?:in\s+)?(\d{4})",
            content_lower
        )
        if death_year_match:
            death_year = int(death_year_match.group(1) or death_year_match.group(2))
            if death_year > current_year:
                issues.append(
                    f"Death year {death_year} is in the future - verify accuracy"
                )
    
    # Subject-specific checks if context provided
    if subject_context:
        context_lower = subject_context.lower()
        if "current" in context_lower and "former" in content_lower:
            suggestions.append(
                "Subject context says 'current' but content uses 'former' - verify"
            )
    
    return {
        "issues_found": len(issues) > 0,
        "issues": issues,
        "suggestions": suggestions,
        "current_date": current_date.strftime("%B %d, %Y"),
        "current_year": current_year,
    }


@tool(
    name="validate_research_subject",
    category=ToolCategory.RESEARCH,
    description=(
        "Validate that scraped content is about the correct research subject. "
        "Helps filter out content about different people with similar names, "
        "obituaries of unrelated people, or context mismatches. "
        "Use after scraping to ensure relevance."
    ),
    return_direct=False,
    requires_api=False,
)
def validate_research_subject(
    content: Annotated[str, "Scraped content to validate"],
    subject_name: Annotated[str, "Name of the research subject"],
    expected_context: Annotated[
        str,
        "Expected context (e.g., 'CEO of Acme', 'born 1960', 'physicist')"
    ] = "",
) -> dict:
    """Validate that content is about the correct research subject.

    Helps avoid including content about:
    - Different people with similar names
    - Obituaries of unrelated people
    - Age/timeline mismatches
    - Occupation/context mismatches

    Args:
        content: Content to validate
        subject_name: Name of research subject
        expected_context: Expected identifying information

    """
    if not content or not subject_name:
        return {
            "likely_match": False,
            "confidence": "uncertain",
            "reasons": ["Missing content or subject name"],
            "red_flags": [],
        }
    
    content_lower = content.lower()
    name_lower = subject_name.lower()
    reasons = []
    red_flags = []
    
    # Check if name appears in content
    name_parts = name_lower.split()
    full_name_found = name_lower in content_lower
    
    if full_name_found:
        reasons.append(f"Full name '{subject_name}' found in content")
    else:
        # Check for partial name matches
        parts_found = sum(1 for part in name_parts if part in content_lower)
        if parts_found >= len(name_parts) - 1:
            reasons.append(f"Name parts found ({parts_found}/{len(name_parts)})")
        else:
            red_flags.append(f"Name not clearly found in content")
    
    # Check for obituary/death notices (might be wrong person)
    obituary_patterns = [
        r"passed away",
        r"died on",
        r"in memoriam",
        r"obituary",
        r"funeral",
        r"survived by",
    ]
    for pattern in obituary_patterns:
        if re.search(pattern, content_lower):
            red_flags.append(f"Content appears to be an obituary - verify correct person")
            break
    
    # Check expected context if provided
    if expected_context:
        context_lower = expected_context.lower()
        context_terms = [term.strip() for term in context_lower.split(",")]
        
        matches = 0
        for term in context_terms:
            if term and term in content_lower:
                matches += 1
                reasons.append(f"Context match: '{term}'")
        
        if matches == 0 and context_terms:
            red_flags.append(f"Expected context not found: {expected_context}")
    
    # Determine confidence
    if len(red_flags) >= 2:
        confidence = "low"
        likely_match = False
    elif len(red_flags) == 1:
        confidence = "medium"
        likely_match = len(reasons) >= 2
    elif len(reasons) >= 2:
        confidence = "high"
        likely_match = True
    else:
        confidence = "medium"
        likely_match = len(reasons) > 0
    
    return {
        "likely_match": likely_match,
        "confidence": confidence,
        "reasons": reasons,
        "red_flags": red_flags,
    }
