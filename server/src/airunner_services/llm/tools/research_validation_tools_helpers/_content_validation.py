"""URL and content validation helpers for research tools."""

import re
from urllib.parse import ParseResult, urlparse

from airunner_services.settings import AIRUNNER_LOG_LEVEL
from airunner_services.utils.application import get_logger

logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)

BLACKLISTED_DOMAINS = {
    "nytimes.com",
    "wsj.com",
    "ft.com",
    "economist.com",
    "bloomberg.com",
    "bakerinstitute.org",
}

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


def validate_url_impl(url: str) -> dict:
    """Validate a URL for research scraping suitability."""
    try:
        parsed = urlparse(url)
        invalid_result = _invalid_url_result(parsed)
        if invalid_result is not None:
            return invalid_result
        domain = _normalized_domain(parsed.netloc)
        blocked_domain = _blocked_domain_result(domain)
        if blocked_domain is not None:
            return blocked_domain
        blocked_path = _blocked_path_result(parsed.path.lower(), domain)
        if blocked_path is not None:
            return blocked_path
        return _url_result(True, "URL is suitable for research scraping", domain)
    except Exception as exc:
        return _url_error_result(exc)


def validate_content_impl(content: str, source_url: str = "") -> dict:
    """Validate scraped content quality and safety."""
    warnings: list[str] = []
    short_result = _short_content_result(content, warnings)
    if short_result is not None:
        return short_result
    blocked_result = _hard_block_result(content.lower(), warnings, len(content))
    if blocked_result is not None:
        return blocked_result
    injection_result = _injection_result(content, source_url, warnings)
    if injection_result is not None:
        return injection_result
    warnings.extend(_content_warnings(content.lower()))
    return _content_result(True, "Content quality acceptable", warnings, len(content))


def _invalid_url_result(parsed: ParseResult) -> dict | None:
    """Return an invalid-result payload for malformed URLs."""
    if not parsed.scheme or not parsed.netloc:
        return _url_result(
            False,
            "Invalid URL format - missing scheme or domain",
            None,
        )
    if parsed.scheme not in ("http", "https"):
        return _url_result(False, f"Unsupported URL scheme: {parsed.scheme}", None)
    return None


def _normalized_domain(netloc: str) -> str:
    """Normalize a parsed netloc into a comparable domain string."""
    domain = netloc.lower()
    if domain.startswith("www."):
        return domain[4:]
    return domain


def _blocked_domain_result(domain: str) -> dict | None:
    """Return the blocked-domain payload when a domain is blacklisted."""
    for blacklisted in BLACKLISTED_DOMAINS:
        if domain == blacklisted or domain.endswith("." + blacklisted):
            reason = (
                f"Domain {domain} is blacklisted "
                f"(typically paywalled or blocks scrapers)"
            )
            return _url_result(False, reason, domain)
    return None


def _blocked_path_result(path: str, domain: str) -> dict | None:
    """Return the blocked-path payload when a path segment is irrelevant."""
    for segment in IRRELEVANT_PATH_SEGMENTS:
        if segment in path:
            reason = (
                "URL contains irrelevant path segment: "
                f"{segment.strip('/')}"
            )
            return _url_result(False, reason, domain)
    return None


def _url_result(valid: bool, reason: str, domain: str | None) -> dict:
    """Build the common URL validation result payload."""
    return {"valid": valid, "reason": reason, "domain": domain}


def _url_error_result(exc: Exception) -> dict:
    """Return the common URL error payload and log the exception."""
    logger.error("URL validation error: %s", exc)
    return _url_result(False, f"Error validating URL: {str(exc)}", None)


def _short_content_result(content: str, warnings: list[str]) -> dict | None:
    """Return the short-content failure payload when content is too small."""
    if content and len(content) >= 200:
        return None
    length = len(content) if content else 0
    reason = "Content too short (< 200 characters) - likely blocked or empty page"
    return _content_result(False, reason, warnings, length)


def _hard_block_result(
    content_lower: str,
    warnings: list[str],
    content_length: int,
) -> dict | None:
    """Return the hard-block payload when blocked content is detected."""
    for phrase in HARD_BLOCK_PHRASES:
        if phrase in content_lower[:2000]:
            reason = f"Content appears blocked: '{phrase}' detected"
            return _content_result(False, reason, warnings, content_length)
    return None


def _injection_result(
    content: str,
    source_url: str,
    warnings: list[str],
) -> dict | None:
    """Return the security payload when prompt-injection text is detected."""
    scan_text = content[:5000] + "\n" + content[-5000:]
    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, scan_text, re.IGNORECASE):
            logger.warning(
                "[Security] Blocked content from %s - injection pattern: '%s'",
                source_url,
                pattern,
            )
            reason = "Security: Potential prompt injection detected"
            return _content_result(False, reason, warnings, len(content))
    return None


def _content_warnings(content_lower: str) -> list[str]:
    """Return non-fatal content warnings."""
    warnings: list[str] = []
    if "cookie" in content_lower[:1000] and "accept" in content_lower[:1000]:
        warnings.append("Page may have cookie consent banner")
    if "javascript" in content_lower[:500] and "enable" in content_lower[:500]:
        warnings.append("Page may require JavaScript for full content")
    return warnings


def _content_result(
    valid: bool,
    reason: str,
    warnings: list[str],
    content_length: int,
) -> dict:
    """Build the common content validation result payload."""
    return {
        "valid": valid,
        "reason": reason,
        "warnings": warnings,
        "content_length": content_length,
    }