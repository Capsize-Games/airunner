"""
Research mode tools for information gathering and synthesis.

Provides tools for:
- Web search and scraping
- Source synthesis and combination
- Citation formatting
- Research organization
"""

from typing import List
from airunner.components.llm.core.tool_registry import tool, ToolCategory
from airunner.settings import AIRUNNER_LOG_LEVEL
from airunner.utils.application import get_logger

logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)


# Note: Web search and scraping tools are currently in web_tools.py
# They will be migrated here in a future update, but for now we create
# complementary research-specific tools


@tool(
    name="synthesize_sources",
    category=ToolCategory.RESEARCH,
    description=(
        "Synthesize information from multiple sources into a coherent summary. "
        "Takes a list of source texts and combines their key points, "
        "identifying common themes and resolving conflicts."
    ),
)
def synthesize_sources(sources: List[str], topic: str = "") -> str:
    """
    Synthesize information from multiple sources.

    Args:
        sources: List of source texts to synthesize
        topic: Optional topic to focus synthesis on

    """
    logger.info(
        f"Synthesizing {len(sources)} sources"
        + (f" on topic: {topic}" if topic else "")
    )

    if not sources:
        return "No sources provided for synthesis."

    # Count total words across sources
    total_words = sum(len(s.split()) for s in sources)

    # Identify common themes (simple keyword extraction)
    all_words = " ".join(sources).lower().split()
    word_freq = {}
    for word in all_words:
        if len(word) > 4:  # Skip short words
            word_freq[word] = word_freq.get(word, 0) + 1

    common_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[
        :5
    ]

    return (
        f"Synthesis of {len(sources)} sources ({total_words} total words):\n\n"
        f"Common themes: {', '.join(w for w, _ in common_words)}\n\n"
        "Key findings:\n"
        f"- Source 1 highlights: {sources[0][:100]}...\n"
        + (
            f"- Source 2 highlights: {sources[1][:100]}...\n"
            if len(sources) > 1
            else ""
        )
        + (
            f"- Additional sources provide supporting evidence\n"
            if len(sources) > 2
            else ""
        )
        + "\n(Full synthesis implementation pending)"
    )


@tool(
    name="cite_sources",
    category=ToolCategory.RESEARCH,
    description=(
        "Format citations in various academic styles (APA, MLA, Chicago). "
        "Provide source information and desired citation style."
    ),
)
def cite_sources(
    title: str,
    authors: List[str] = None,
    year: str = "",
    url: str = "",
    style: str = "APA",
) -> str:
    """
    Format academic citations.

    Args:
        title: Title of the source
        authors: List of author names
        year: Publication year
        url: URL if online source
        style: Citation style (APA, MLA, Chicago)

    """
    logger.info(f"Formatting citation in {style} style")

    authors = authors or ["Unknown Author"]
    author_str = ", ".join(authors[:3])  # First 3 authors
    if len(authors) > 3:
        author_str += ", et al."

    if style.upper() == "APA":
        citation = f"{author_str} ({year}). {title}."
        if url:
            citation += f" Retrieved from {url}"
    elif style.upper() == "MLA":
        citation = f'{author_str}. "{title}." {year}.'
        if url:
            citation += f" Web. <{url}>"
    elif style.upper() == "CHICAGO":
        citation = f'{author_str}. "{title}." {year}.'
        if url:
            citation += f" Accessed at {url}."
    else:
        citation = f"{author_str}. {title}. {year}. {url}"

    return citation


@tool(
    name="organize_research",
    category=ToolCategory.RESEARCH,
    description=(
        "Organize research findings into a structured outline with topics, "
        "subtopics, and key points. Useful for organizing notes and planning papers."
    ),
)
def organize_research(findings: str, structure_type: str = "outline") -> str:
    """
    Organize research findings into a structure.

    Args:
        findings: Raw research findings text
        structure_type: Type of structure (outline, mind_map, categories)

    """
    logger.info(f"Organizing research as {structure_type}")

    # Split into paragraphs/sections
    sections = [s.strip() for s in findings.split("\n\n") if s.strip()]

    if structure_type == "outline":
        outline = "Research Outline:\n\n"
        for i, section in enumerate(sections, 1):
            outline += f"{i}. {section[:100]}...\n"
            # Add sub-points (simplified)
            sentences = section.split(". ")
            for j, sent in enumerate(sentences[:3], 1):
                if sent.strip():
                    outline += f"   {chr(96+j)}. {sent[:50]}...\n"
            outline += "\n"
        return outline

    elif structure_type == "categories":
        return (
            f"Research Categories ({len(sections)} main topics):\n\n"
            + "\n".join(
                f"Category {i}: {s[:80]}..." for i, s in enumerate(sections, 1)
            )
        )

    else:
        return f"Organized {len(sections)} research sections (full implementation pending)"


@tool(
    name="extract_key_points",
    category=ToolCategory.RESEARCH,
    description=(
        "Extract key points and main ideas from a research text. "
        "Identifies the most important information and creates a bulleted summary."
    ),
)
def extract_key_points(text: str, max_points: int = 5) -> str:
    """
    Extract key points from text.

    Args:
        text: The text to extract key points from
        max_points: Maximum number of key points to extract

    """
    logger.info(f"Extracting up to {max_points} key points")

    # Split into sentences
    sentences = []
    for s in text.replace("! ", ".|").replace("? ", ".|").split(".|"):
        s = s.strip()
        if s and len(s) > 20:  # Filter very short fragments
            sentences.append(s)

    # Score sentences by length and position (simple heuristic)
    scored = []
    for i, sent in enumerate(sentences):
        # Earlier sentences and moderate length get higher scores
        score = (1.0 / (i + 1)) * min(len(sent.split()), 30) / 30
        scored.append((score, sent))

    # Get top N sentences
    scored.sort(reverse=True)
    key_points = [sent for _, sent in scored[:max_points]]

    result = f"Key Points (extracted {len(key_points)} from {len(sentences)} sentences):\n\n"
    for i, point in enumerate(key_points, 1):
        result += f"{i}. {point}\n"

    return result


@tool(
    name="compare_sources",
    category=ToolCategory.RESEARCH,
    description=(
        "Compare multiple sources on the same topic, identifying agreements, "
        "disagreements, and unique perspectives from each source."
    ),
)
def compare_sources(source1: str, source2: str, source3: str = "") -> str:
    """
    Compare multiple sources.

    Args:
        source1: First source text
        source2: Second source text
        source3: Optional third source text

    """
    logger.info("Comparing sources")

    sources = [s for s in [source1, source2, source3] if s]

    # Calculate overlap (simple word-based)
    words1 = set(source1.lower().split())
    words2 = set(source2.lower().split())
    overlap = words1 & words2

    overlap_pct = (
        len(overlap) / max(len(words1), len(words2)) * 100
        if words1 or words2
        else 0
    )

    return (
        f"Source Comparison ({len(sources)} sources):\n\n"
        f"Source 1: {len(source1)} characters, {len(source1.split())} words\n"
        f"Source 2: {len(source2)} characters, {len(source2.split())} words\n"
        + (
            f"Source 3: {len(source3)} characters, {len(source3.split())} words\n"
            if source3
            else ""
        )
        + f"\nContent overlap: {overlap_pct:.1f}%\n"
        + f"Common themes: {', '.join(list(overlap)[:5])}\n\n"
        "Unique perspectives:\n"
        f"- Source 1: {source1[:100]}...\n"
        f"- Source 2: {source2[:100]}...\n"
        + (f"- Source 3: {source3[:100]}...\n" if source3 else "")
        + "\n(Detailed comparison implementation pending)"
    )
