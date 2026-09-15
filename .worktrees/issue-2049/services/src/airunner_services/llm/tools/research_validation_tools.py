"""Research validation tool registrations."""

from typing import Annotated

from airunner_services.llm.core.tool_registry import ToolCategory, tool
from airunner_services.llm.tools.research_validation_tools_helpers import (
    check_temporal_accuracy_impl,
    extract_age_from_text_impl,
    get_current_date_context_impl,
    validate_content_impl,
    validate_research_subject_impl,
    validate_url_impl,
)


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
    """Validate a URL for research scraping suitability."""
    return validate_url_impl(url)


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
    """Validate scraped content quality and safety."""
    return validate_content_impl(content, source_url)


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
    """Extract approximate age from text content."""
    return extract_age_from_text_impl(content)


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
    """Get current date information for temporal validation."""
    return get_current_date_context_impl()


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
    """Check content for temporal accuracy issues."""
    return check_temporal_accuracy_impl(content, subject_context)


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
    """Validate that content is about the correct research subject."""
    return validate_research_subject_impl(
        content,
        subject_name,
        expected_context,
    )
