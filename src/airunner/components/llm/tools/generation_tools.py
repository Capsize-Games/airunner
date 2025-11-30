"""
Direct text generation tools.

Tools for generating text output without conversational wrappers.
These tools are designed for tasks requiring factual, descriptive, or
structured output rather than chat-style responses.
"""

from typing import Annotated, Any

from airunner.components.llm.core.tool_registry import tool, ToolCategory


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
    requires_agent=True,
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
        agent: The agent instance (automatically injected)

    """
    if not agent:
        return "Error: Agent not available"

    # Use the agent's generation capabilities directly
    # The system prompt override will be handled by the caller
    # This tool simply signals that direct generation is requested

    # Return a marker that tells the workflow manager to use direct generation
    # The actual generation happens in the workflow
    return f"__DIRECT_GENERATION_REQUEST__:{prompt}"


@tool(
    name="generate_description",
    category=ToolCategory.GENERATION,
    description=(
        "Generate a concise description or summary (3-5 sentences) without "
        "conversational preamble. Use for book descriptions, content summaries, "
        "product descriptions, etc. Returns only the description text."
    ),
    return_direct=True,
    requires_agent=True,
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
        agent: The agent instance (automatically injected)

    """
    if not agent:
        return "Error: Agent not available"

    # Create a focused prompt for direct description generation
    generation_prompt = (
        f"Write a book-jacket description for: {subject}\n\n"
        f"Based on this content:\n{context[:1000]}\n\n"  # Limit context to avoid overwhelming
        f"Write ONLY the description (3-5 sentences). "
        f"Start directly with the description, no preamble like 'Here is' or 'This book'."
    )

    # Return a marker that tells the workflow manager to use direct generation
    # The actual generation happens in the workflow; include the prompt after marker
    return f"__DIRECT_GENERATION_REQUEST__:{generation_prompt}"


@tool(
    name="categorize",
    category=ToolCategory.ANALYSIS,
    description=(
        "Categorize or classify content into a single category. "
        "Returns only the category name without explanation or preamble."
    ),
    return_direct=True,
    requires_agent=True,
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
        agent: The agent instance (automatically injected)

    """
    if not agent:
        return "Error: Agent not available"

    prompt = f"Subject: {subject}\n\nContent: {content}\n\nReturn only the category name."
    return f"__DIRECT_GENERATION_REQUEST__:{prompt}"
