"""Side-effect-free formatting for registered knowledge-base records."""

import os
from typing import Any


def format_knowledge_base_results(
    top_docs: list[tuple[int, Any]], *, query: str
) -> str:
    """Render ranked records without discovery or implicit indexing."""
    parts = [f"Found {len(top_docs)} relevant document(s) for '{query}':\n"]
    for index, (_score, doc) in enumerate(top_docs, 1):
        status = "indexed" if doc.indexed else "not indexed"
        parts.extend(
            (
                f"{index}. {os.path.basename(doc.path)} ({status})",
                f"   Path: {doc.path}",
            )
        )
    parts.append(
        "\nTip: Use these document paths with rag_search to get detailed content."
    )
    return "\n".join(parts)


def no_documents_message() -> str:
    """Return the message used when the registered catalog is empty."""
    return (
        "No documents found in knowledge base. "
        "⚠️ Try search_web() to search the internet instead, "
        "then use record_knowledge() to save any useful facts."
    )


def no_matches_message(query: str) -> str:
    """Return the message used when no catalog paths match a query."""
    return (
        "No documents found matching "
        f"'{query}' in the knowledge base. "
        f"⚠️ Try search_web('{query}') to search the internet instead, "
        "then use record_knowledge() to save any useful facts you find."
    )
