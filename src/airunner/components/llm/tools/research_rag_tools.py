"""
RAG-based research tools for Deep Research Agent.

Provides tools for:
- Indexing research notes into RAG
- Searching documents by semantic chunks
- Maintaining running summaries
"""

import os
import re
from pathlib import Path
from typing import Annotated, Any, List, Dict

from airunner.components.llm.core.tool_registry import tool, ToolCategory
from airunner.settings import AIRUNNER_LOG_LEVEL
from airunner.utils.application import get_logger

logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)


@tool(
    name="search_document_chunks",
    category=ToolCategory.RESEARCH,
    description=(
        "Search through a document by semantic chunks. "
        "Finds the most relevant sections of a document based on your query. "
        "Use this to find specific information in long research notes or documents."
    ),
    return_direct=False,
)
def search_document_chunks(
    query: Annotated[
        str,
        "What to search for (e.g., 'sanctions timeline', 'cabinet meetings')",
    ],
    document_path: Annotated[str, "Absolute path to the document to search"],
    max_results: Annotated[int, "Maximum number of chunks to return"] = 5,
) -> str:
    """
    Search a document by chunks and return relevant sections.

    Args:
        query: Search query
        document_path: Path to document
        max_results: Max chunks to return

    """
    try:
        if not os.path.exists(document_path):
            return f"Error: Document not found at {document_path}"

        # Read document
        with open(document_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Split into chunks (by sections/paragraphs)
        chunks = _split_into_chunks(content)

        if not chunks:
            return "Error: No content found in document"

        # Simple keyword-based ranking (can be enhanced with embeddings)
        query_lower = query.lower()
        query_words = set(query_lower.split())

        # Score each chunk
        scored_chunks = []
        for i, chunk in enumerate(chunks):
            chunk_lower = chunk.lower()
            # Count query word matches
            matches = sum(1 for word in query_words if word in chunk_lower)
            # Prefer chunks with more matches and shorter length
            score = matches * 100 / (len(chunk.split()) + 1)
            scored_chunks.append((score, i, chunk))

        # Sort by score and get top results
        scored_chunks.sort(reverse=True, key=lambda x: x[0])
        top_chunks = scored_chunks[:max_results]

        if not top_chunks or top_chunks[0][0] == 0:
            return f"No relevant information found for query: {query}"

        # Format results
        results = [f"Search results for: {query}\n"]
        results.append(f"Found {len(top_chunks)} relevant sections:\n")

        for score, idx, chunk in top_chunks:
            if score > 0:  # Only include chunks with matches
                # Truncate very long chunks
                display_chunk = (
                    chunk[:800] + "..." if len(chunk) > 800 else chunk
                )
                results.append(
                    f"\n--- Section {idx + 1} (relevance: {score:.1f}) ---"
                )
                results.append(display_chunk)

        return "\n".join(results)

    except Exception as e:
        logger.error(f"Failed to search document chunks: {e}")
        return f"Error searching document: {str(e)}"


def _split_into_chunks(content: str, chunk_size: int = 1000) -> List[str]:
    """Split document into semantic chunks.

    Args:
        content: Document content
        chunk_size: Target chunk size in characters

    """
    chunks = []

    # First try to split by markdown headers
    if "###" in content or "##" in content:
        # Split by headers, keeping header with content
        pattern = r"(###[^\n]+\n.*?)(?=###|\Z)"
        sections = re.findall(pattern, content, re.DOTALL)

        if sections:
            for section in sections:
                # If section is too large, split further
                if len(section) > chunk_size * 2:
                    # Split by paragraphs
                    paragraphs = section.split("\n\n")
                    current_chunk = []
                    current_size = 0

                    for para in paragraphs:
                        para_size = len(para)
                        if (
                            current_size + para_size > chunk_size
                            and current_chunk
                        ):
                            chunks.append("\n\n".join(current_chunk))
                            current_chunk = [para]
                            current_size = para_size
                        else:
                            current_chunk.append(para)
                            current_size += para_size

                    if current_chunk:
                        chunks.append("\n\n".join(current_chunk))
                else:
                    chunks.append(section)

            return chunks

    # Fallback: split by paragraphs
    paragraphs = content.split("\n\n")
    current_chunk = []
    current_size = 0

    for para in paragraphs:
        para_size = len(para)
        if current_size + para_size > chunk_size and current_chunk:
            chunks.append("\n\n".join(current_chunk))
            current_chunk = [para]
            current_size = para_size
        else:
            current_chunk.append(para)
            current_size += para_size

    if current_chunk:
        chunks.append("\n\n".join(current_chunk))

    return chunks if chunks else [content]


@tool(
    name="update_research_summary",
    category=ToolCategory.RESEARCH,
    description=(
        "Update the running research summary document. "
        "This maintains a concise summary of all research notes collected so far. "
        "The summary is rewritten (not appended) each time with new information."
    ),
    return_direct=False,
    requires_api=True,
)
def update_research_summary(
    notes_path: Annotated[str, "Path to the research notes file"],
    summary_content: Annotated[str, "The new summary content to write"],
    api: Any = None,
) -> str:
    """
    Update the research summary document.

    Args:
        notes_path: Path to notes file (used to derive summary path)
        summary_content: New summary to write
        api: API instance

    """
    try:
        # Derive summary path from notes path
        notes_path_obj = Path(notes_path)
        summary_path = (
            notes_path_obj.parent / f"{notes_path_obj.stem}.summary.md"
        )

        # Write summary
        with open(summary_path, "w", encoding="utf-8") as f:
            f.write(summary_content)

        logger.info(f"Updated research summary: {summary_path}")
        return f"Successfully updated research summary at {summary_path}"

    except Exception as e:
        logger.error(f"Failed to update research summary: {e}")
        return f"Error updating summary: {str(e)}"


@tool(
    name="get_research_summary",
    category=ToolCategory.RESEARCH,
    description=(
        "Get the current research summary. "
        "Returns the running summary of all research notes collected so far."
    ),
    return_direct=False,
)
def get_research_summary(
    notes_path: Annotated[str, "Path to the research notes file"],
) -> str:
    """
    Get the current research summary.

    Args:
        notes_path: Path to notes file (used to derive summary path)

    """
    try:
        # Derive summary path from notes path
        notes_path_obj = Path(notes_path)
        summary_path = (
            notes_path_obj.parent / f"{notes_path_obj.stem}.summary.md"
        )

        if not summary_path.exists():
            return "No summary available yet."

        with open(summary_path, "r", encoding="utf-8") as f:
            content = f.read()

        return content

    except Exception as e:
        logger.error(f"Failed to get research summary: {e}")
        return f"Error reading summary: {str(e)}"
