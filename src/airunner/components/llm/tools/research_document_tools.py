"""
Research document management tools.

Provides tools for creating, locking, and managing research documents
during the Deep Research workflow. Documents are created in the document
editor and locked to prevent user editing while the LLM is working.
"""

import os
from datetime import datetime
from typing import Annotated, Any

from airunner.components.llm.core.tool_registry import tool, ToolCategory
from airunner.settings import AIRUNNER_LOG_LEVEL
from airunner.utils.application import get_logger
from airunner.enums import SignalCode

logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)

# Research document template
RESEARCH_DOCUMENT_TEMPLATE = """# {title}

**Research Date:** {date}  
**Research Started:** {datetime_started}  
**Status:** In Progress

---
"""


@tool(
    name="create_research_document",
    category=ToolCategory.RESEARCH,
    description=(
        "Create a new research document in the document editor. "
        "Returns the file path. The document will be locked for editing by the LLM. "
        "Use this at the start of deep research to create the main research document."
    ),
    return_direct=False,
    requires_api=True,
)
def create_research_document(
    topic: Annotated[str, "The research topic/title"],
    api: Any = None,
) -> str:
    """
    Create a new research document.

    Creates a markdown file in text/other/research/ with a standardized
    academic template. The document is automatically opened in the editor
    and locked to prevent user modifications.

    Args:
        topic: Research topic/title
        api: API instance (injected automatically)

    """
    if not api:
        return "Error: API not available"

    try:
        # Get base path from settings
        base_path = api.path_settings.base_path
        research_dir = os.path.join(base_path, "text", "other", "research")
        os.makedirs(research_dir, exist_ok=True)

        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_topic = "".join(
            c for c in topic if c.isalnum() or c in (" ", "_", "-")
        ).replace(" ", "_")[:50]
        filename = f"{safe_topic}_{timestamp}.md"
        filepath = os.path.join(research_dir, filename)

        # Create document from template
        content = RESEARCH_DOCUMENT_TEMPLATE.format(
            title=topic,
            date=datetime.now().strftime("%B %d, %Y"),
            datetime_started=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )

        # Write the file
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

        logger.info(f"Created research document: {filepath}")

        # Signal to open document in editor (locked)
        api.emit_signal(
            SignalCode.OPEN_RESEARCH_DOCUMENT,
            {"path": filepath, "locked": True, "title": topic},
        )

        return filepath

    except Exception as e:
        logger.error(f"Failed to create research document: {e}", exc_info=True)
        return f"Error creating research document: {str(e)}"


@tool(
    name="create_research_notes",
    category=ToolCategory.RESEARCH,
    description=(
        "Create a temporary notes file for incremental research notes. "
        "This file stores findings from web searches organized by URL. "
        "Use this to accumulate research before writing the main document."
    ),
    return_direct=False,
    requires_api=True,
)
def create_research_notes(
    topic: Annotated[str, "The research topic (should match main document)"],
    api: Any = None,
) -> str:
    """
    Create a research notes file.

    Creates a markdown file for temporary notes during research.
    Notes are organized by source URL.

    Args:
        topic: Research topic (should match main document)
        api: API instance (injected automatically)

    """
    if not api:
        return "Error: API not available"

    try:
        base_path = api.path_settings.base_path
        research_dir = os.path.join(base_path, "text", "other", "research")
        os.makedirs(research_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_topic = "".join(
            c for c in topic if c.isalnum() or c in (" ", "_", "-")
        ).replace(" ", "_")[:50]
        filename = f"{safe_topic}_{timestamp}_notes.md"
        filepath = os.path.join(research_dir, filename)

        # Create notes file
        content = f"""# Research Notes: {topic}

**Date:** {datetime.now().strftime("%B %d, %Y %H:%M")}

---

## Research Sources

"""
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

        logger.info(f"Created research notes: {filepath}")

        # Signal to open notes in editor (read-only/locked during research)
        if api and hasattr(api, "emit_signal"):
            api.emit_signal(
                SignalCode.OPEN_RESEARCH_DOCUMENT,
                {"path": filepath, "locked": True, "title": f"Notes: {topic}"},
            )

        return filepath

    except Exception as e:
        logger.error(f"Failed to create notes file: {e}", exc_info=True)
        return f"Error creating notes file: {str(e)}"


@tool(
    name="append_research_notes",
    category=ToolCategory.RESEARCH,
    description=(
        "Append findings from a source to the research notes file. "
        "Organizes notes by URL with header and content. "
        "Use this after scraping each web page during research phase."
    ),
    return_direct=False,
    requires_api=True,
)
def append_research_notes(
    notes_path: Annotated[str, "Path to the notes file"],
    source_url: Annotated[str, "URL of the source"],
    findings: Annotated[str, "Key findings/summary from this source"],
    api: Any = None,
) -> str:
    """
    Append findings to research notes.

    Args:
        notes_path: Path to notes file
        source_url: URL of source
        findings: Summary of findings

    """
    try:
        # Build the entry
        entry = f"""
### {source_url}

**Retrieved:** {datetime.now().strftime("%Y-%m-%d %H:%M")}

{findings}

---

"""

        # Append to file
        with open(notes_path, "a", encoding="utf-8") as f:
            f.write(entry)

        # Stream the content to open document (if any)
        if api:
            # Send the full entry as a streaming update
            api.emit_signal(
                SignalCode.STREAM_TO_DOCUMENT,
                {"path": notes_path, "chunk": entry},
            )

        logger.info(f"Appended notes from {source_url}")
        return f"Successfully added notes from {source_url}"

    except Exception as e:
        logger.error(f"Failed to append notes: {e}", exc_info=True)
        return f"Error appending notes: {str(e)}"


@tool(
    name="update_research_section",
    category=ToolCategory.RESEARCH,
    description=(
        "Update a specific section of the research document. "
        "Can update Abstract, Introduction, body sections, Conclusion, or Sources. "
        "Use this to incrementally build the research document."
    ),
    return_direct=False,
    requires_api=True,
)
def update_research_section(
    document_path: Annotated[str, "Path to the research document"],
    section_name: Annotated[
        str,
        "Section to update (e.g., 'Abstract', 'Introduction', 'Conclusion')",
    ],
    content: Annotated[str, "New content for the section"],
    api: Any = None,
) -> str:
    """
    Update a section of the research document.

    Args:
        document_path: Path to research document
        section_name: Name of section to update
        content: New content
        api: API instance (injected automatically)

    """
    try:
        # Read current document
        with open(document_path, "r", encoding="utf-8") as f:
            doc_content = f.read()

        # Find and replace section
        # Look for "## {section_name}" and replace until next "##" or "---"
        import re

        # Pattern to match section header and content until next section
        # Matches: optional whitespace, "## Section", newline, content until next "##" or "---" or end
        pattern = rf"^[ \t]*## {re.escape(section_name)}\s*\n(.*?)(?=^[ \t]*##|^---|\Z)"

        def replace_section(match):
            # Return just the header and new content (preserve proper spacing)
            return f"## {section_name}\n\n{content}\n\n"

        new_content, count = re.subn(
            pattern,
            replace_section,
            doc_content,
            flags=re.DOTALL | re.MULTILINE,
        )

        if count == 0:
            # Section not found, append it before final "---" or at end
            # Try to insert before the final document separator
            if "\n---\n" in doc_content:
                # Insert before the last "---"
                parts = doc_content.rsplit("\n---\n", 1)
                new_content = f"{parts[0]}\n\n## {section_name}\n\n{content}\n\n---\n{parts[1]}"
            else:
                # No separator, just append
                new_content = (
                    f"{doc_content}\n\n## {section_name}\n\n{content}\n"
                )
            logger.info(f"Added new section: {section_name}")
        else:
            logger.info(
                f"Updated section: {section_name} (replaced {count} occurrence(s))"
            )

        # Write updated document
        with open(document_path, "w", encoding="utf-8") as f:
            f.write(new_content)

        # Signal to update the document in memory
        if api:
            api.emit_signal(
                SignalCode.UPDATE_DOCUMENT_CONTENT,
                {
                    "path": document_path,
                    "content": new_content,
                    "append": False,
                },
            )
            logger.info(f"Signaled document update for: {document_path}")

        return f"Successfully updated {section_name} section"

    except Exception as e:
        logger.error(f"Failed to update section: {e}", exc_info=True)
        return f"Error updating section: {str(e)}"


@tool(
    name="add_source_citation",
    category=ToolCategory.RESEARCH,
    description=(
        "Add a source citation to the Sources section of the research document. "
        "Formats citations with title, URL, and access date. "
        "Use this to build the bibliography as research progresses."
    ),
    return_direct=False,
    requires_api=False,
)
def add_source_citation(
    document_path: Annotated[str, "Path to the research document"],
    title: Annotated[str, "Title of the source"],
    url: Annotated[str, "URL of the source"],
    author: Annotated[
        str, "Author (if known, otherwise 'Unknown')"
    ] = "Unknown",
) -> str:
    """
    Add a citation to the Sources section.

    Args:
        document_path: Path to research document
        title: Source title
        url: Source URL
        author: Author name

    """
    try:
        # Read current document
        with open(document_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Find Sources section
        import re

        access_date = datetime.now().strftime("%B %d, %Y")

        citation = f"""
- **{title}**  
  Author: {author}  
  URL: [{url}]({url})  
  Accessed: {access_date}
"""

        # Find Sources section and append
        pattern = r"(## Sources\s*\n)(.*?)(?=\n##|\Z)"

        def add_citation(match):
            existing = match.group(2).strip()
            if "[To be added" in existing or not existing:
                # Replace placeholder
                return f"{match.group(1)}\n{citation}"
            else:
                # Append to existing
                return f"{match.group(1)}{existing}\n{citation}"

        new_content, count = re.subn(
            pattern, add_citation, content, flags=re.DOTALL
        )

        if count == 0:
            # Sources section not found, add it
            new_content = content + f"\n\n## Sources\n{citation}\n"

        with open(document_path, "w", encoding="utf-8") as f:
            f.write(new_content)

        logger.info(f"Added citation: {title}")
        return f"Successfully added citation for {title}"

    except Exception as e:
        logger.error(f"Failed to add citation: {e}", exc_info=True)
        return f"Error adding citation: {str(e)}"


@tool(
    name="finalize_research_document",
    category=ToolCategory.RESEARCH,
    description=(
        "Mark research document as complete and unlock it for user viewing/editing. "
        "Updates status and signals the editor to unlock the document."
    ),
    return_direct=False,
    requires_api=True,
)
def finalize_research_document(
    document_path: Annotated[str, "Path to the research document"],
    api: Any = None,
) -> str:
    """
    Finalize and unlock research document.

    Args:
        document_path: Path to research document
        api: API instance

    """
    if not api:
        return "Error: API not available"

    try:
        # Update status in document
        with open(document_path, "r", encoding="utf-8") as f:
            content = f.read()

        content = content.replace(
            "**Status:** In Progress", "**Status:** Complete"
        )

        with open(document_path, "w", encoding="utf-8") as f:
            f.write(content)

        # Signal to unlock document
        api.emit_signal(
            SignalCode.UNLOCK_RESEARCH_DOCUMENT,
            {"path": document_path},
        )

        logger.info(f"Finalized research document: {document_path}")
        return f"Research document completed and unlocked: {document_path}"

    except Exception as e:
        logger.error(f"Failed to finalize document: {e}", exc_info=True)
        return f"Error finalizing document: {str(e)}"


@tool(
    name="load_indexed_documents_into_rag",
    category=ToolCategory.RESEARCH,
    description=(
        "Search for and load indexed documents related to a research topic "
        "into RAG context. Use this BEFORE starting web research to incorporate "
        "existing knowledge from the local knowledge base."
    ),
    return_direct=False,
    requires_api=True,
)
def load_indexed_documents_into_rag(
    query: Annotated[
        str,
        "Research topic or query to find relevant indexed documents",
    ],
    max_documents: Annotated[
        int, "Maximum number of documents to load (default 5)"
    ] = 5,
    api: Any = None,
) -> str:
    """Search indexed documents and load relevant ones into RAG context.

    This tool combines document discovery and loading in one step. It:
    1. Searches the knowledge base for documents matching the query
    2. Filters for indexed documents only
    3. Loads them into RAG context for use in research

    Use this at the beginning of research to incorporate existing knowledge
    from your local knowledge base before searching the web.

    Args:
        query: Research topic or query to find relevant documents
        max_documents: Maximum number of documents to load (default 5)
        api: API instance (injected)


    Usage:
        load_indexed_documents_into_rag("machine learning transformers", 3)
    """
    try:
        from airunner.components.documents.data.models.document import Document
        from airunner.components.data.session_manager import session_scope

        logger.info(f"Loading indexed documents for query: {query}")

        # Search for indexed documents
        with session_scope() as session:
            docs = (
                session.query(Document)
                .filter_by(active=True, indexed=True)
                .all()
            )

            if not docs:
                return (
                    "No indexed documents found in knowledge base. "
                    "Proceeding with web-only research."
                )

            # Score documents by relevance
            query_lower = query.lower()
            query_terms = query_lower.split()

            scored_docs = []
            for doc in docs:
                path_lower = doc.path.lower()
                filename = os.path.basename(path_lower)

                score = 0
                for term in query_terms:
                    if term in filename:
                        score += 10
                    elif term in path_lower:
                        score += 5

                if score > 0:
                    scored_docs.append((score, doc))

            # Sort and take top N
            scored_docs.sort(reverse=True, key=lambda x: x[0])
            top_docs = scored_docs[:max_documents]

            if not top_docs:
                return (
                    f"No indexed documents match '{query}'. "
                    f"Proceeding with web-only research."
                )

            # Load documents into RAG
            rag_manager = getattr(api, "rag_manager", None) if api else None

            if not rag_manager:
                # RAG not available, return document paths for reference
                result_parts = [
                    f"Found {len(top_docs)} relevant indexed document(s), "
                    f"but RAG manager not available:\n"
                ]
                for i, (score, doc) in enumerate(top_docs, 1):
                    filename = os.path.basename(doc.path)
                    result_parts.append(f"{i}. {filename}")
                    result_parts.append(f"   Path: {doc.path}")
                return "\n".join(result_parts)

            # Actually load into RAG and search
            loaded_docs = []
            excerpts = []

            for score, doc in top_docs:
                try:
                    # Check if document is already in RAG by searching
                    # If not, we'd need to trigger indexing via signal
                    # For now, just search RAG with the query
                    results = rag_manager.search(query, k=2)

                    if results:
                        for result in results:
                            source = result.metadata.get("source", "unknown")
                            if source == doc.path:
                                content = (
                                    result.page_content[:300]
                                    if len(result.page_content) > 300
                                    else result.page_content
                                )
                                excerpts.append(
                                    f"[{os.path.basename(doc.path)}]\n{content}"
                                )
                                loaded_docs.append(os.path.basename(doc.path))
                                break
                except Exception as e:
                    logger.warning(f"Failed to search RAG for {doc.path}: {e}")
                    continue

            # Format response
            if loaded_docs:
                result_parts = [
                    f"Loaded {len(loaded_docs)} indexed document(s) into "
                    f"RAG context for '{query}':\n"
                ]
                for doc_name in loaded_docs:
                    result_parts.append(f"- {doc_name}")

                if excerpts:
                    result_parts.append("\nRelevant excerpts:")
                    result_parts.extend(excerpts)

                result_parts.append(
                    "\nThese documents are now available for rag_search. "
                    "Use rag_search to find specific information from them."
                )
                return "\n\n".join(result_parts)
            else:
                # Documents found but not loaded in RAG yet
                result_parts = [
                    f"Found {len(top_docs)} relevant indexed document(s) "
                    f"for '{query}':\n"
                ]
                for i, (score, doc) in enumerate(top_docs, 1):
                    filename = os.path.basename(doc.path)
                    result_parts.append(f"{i}. {filename}")

                result_parts.append(
                    "\nNote: These documents are indexed but may not be "
                    "loaded into RAG yet. Proceeding with web research."
                )
                return "\n".join(result_parts)

    except Exception as e:
        logger.error(f"Error loading indexed documents: {e}", exc_info=True)
        return (
            f"Error loading indexed documents: {str(e)}. "
            f"Proceeding with web-only research."
        )


@tool(
    name="edit_document_find_replace",
    category=ToolCategory.RESEARCH,
    description=(
        "Edit a document by finding and replacing text. "
        "Supports simple string replacement and regular expressions. "
        "Use this for precise edits, correcting errors, or updating specific parts of the document."
    ),
    return_direct=False,
    requires_api=True,
)
def edit_document_find_replace(
    document_path: Annotated[str, "Path to the document to edit"],
    find_text: Annotated[str, "Text or pattern to find"],
    replace_text: Annotated[str, "Text to replace with"],
    is_regex: Annotated[
        bool, "Whether find_text is a regular expression"
    ] = False,
    api: Any = None,
) -> str:
    """
    Edit a document using find and replace.

    Args:
        document_path: Path to the document
        find_text: Text to find
        replace_text: Replacement text
        is_regex: Treat find_text as regex
        api: API instance

    """
    import re

    try:
        if not os.path.exists(document_path):
            return f"Error: Document not found at {document_path}"

        # Read current document
        with open(document_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Perform replacement
        if is_regex:
            new_content, count = re.subn(find_text, replace_text, content)
        else:
            count = content.count(find_text)
            new_content = content.replace(find_text, replace_text)

        if count == 0:
            return f"Text not found: '{find_text}'"

        # Write updated document
        with open(document_path, "w", encoding="utf-8") as f:
            f.write(new_content)

        logger.info(
            f"Updated document {document_path}: replaced {count} occurrence(s) of '{find_text}'"
        )

        # Signal to update the document in memory
        if api:
            api.emit_signal(
                SignalCode.UPDATE_DOCUMENT_CONTENT,
                {
                    "path": document_path,
                    "content": new_content,
                    "append": False,
                },
            )
            logger.info(f"Signaled document update for: {document_path}")

        return f"Successfully replaced {count} occurrence(s) of text."

    except Exception as e:
        logger.error(f"Failed to edit document: {e}", exc_info=True)
        return f"Error editing document: {str(e)}"
