"""
Direct text generation tools.

Tools for generating text output without conversational wrappers.
These tools are designed for tasks requiring factual, descriptive, or
structured output rather than chat-style responses.
"""

from typing import Annotated, Any

from airunner.components.llm.core.tool_registry import tool, ToolCategory


DIRECT_GENERATION_REQUEST_PREFIX = "__DIRECT_GENERATION_REQUEST__:"


def _build_direct_generation_request(prompt: str) -> str:
    """Return the internal marker used by direct-generation tools."""
    return f"{DIRECT_GENERATION_REQUEST_PREFIX}{prompt}"


@tool(
    name="generate_direct_response",
    category=ToolCategory.GENERATION,
    description=(
        "Generate direct text output without conversational wrappers or preamble. "
        "Use this for factual descriptions, summaries, classifications, or any task "
        "that requires clean text output without 'It seems...', 'Here's...', or similar "
        "conversational phrases. Returns the generated text directly to the caller."
    ),
    return_direct=True,
    requires_agent=False,
)
def generate_direct_response(
    prompt: Annotated[str, "The generation prompt or instruction"],
    agent: Any = None,
) -> str:
    """
    Generate direct text without conversational wrappers.

    This tool forces the model to produce clean, direct text output
    suitable for descriptions, classifications, summaries, etc.

    Args:
        prompt: The generation task to perform
        agent: Unused compatibility argument

    """
    _ = agent
    return _build_direct_generation_request(prompt)


@tool(
    name="generate_description",
    category=ToolCategory.GENERATION,
    description=(
        "Generate a concise description or summary (3-5 sentences) without "
        "conversational preamble. Use for book descriptions, content summaries, "
        "product descriptions, etc. Returns only the description text."
    ),
    return_direct=True,
    requires_agent=False,
)
def generate_description(
    subject: Annotated[
        str, "What to describe (e.g., book title, product name)"
    ],
    context: Annotated[str, "Relevant context or content to analyze"],
    agent: Any = None,
) -> str:
    """
    Generate a description without conversational formatting.

    Args:
        subject: The subject to describe
        context: Context or content to base the description on
        agent: Unused compatibility argument

    """
    _ = agent

    generation_prompt = (
        f"Write a book-jacket description for: {subject}\n\n"
        f"Based on this content:\n{context[:1000]}\n\n"
        f"Write ONLY the description (3-5 sentences). "
        f"Start directly with the description, no preamble like 'Here is' or 'This book'."
    )
    return _build_direct_generation_request(generation_prompt)


@tool(
    name="categorize",
    category=ToolCategory.ANALYSIS,
    description=(
        "Categorize or classify content into a single category. "
        "Returns only the category name without explanation or preamble."
    ),
    return_direct=True,
    requires_agent=False,
)
def categorize(
    subject: Annotated[str, "What to categorize"],
    content: Annotated[str, "Content to analyze for categorization"],
    agent: Any = None,
) -> str:
    """
    Categorize content without conversational formatting.

    Args:
        subject: The subject being categorized
        content: Content to analyze
        agent: Unused compatibility argument

    """
    _ = agent

    prompt = f"Subject: {subject}\n\nContent: {content}\n\nReturn only the category name."
    return _build_direct_generation_request(prompt)
