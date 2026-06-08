"""
Recall knowledge tool.

Searches the knowledge base using semantic (RAG), keyword,
and TF-IDF backends.
"""

from typing import Annotated, Any

from airunner_services.llm.core.tool_registry import tool, ToolCategory
from airunner_services.settings import AIRUNNER_LOG_LEVEL
from airunner_services.utils.application import get_logger

from ._helpers import merge_search_results

logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)


@tool(
    name="recall_knowledge",
    category=ToolCategory.KNOWLEDGE,
    description=(
        "Search the knowledge base for relevant facts. Uses semantic "
        "search (RAG) to find facts related to the query across all "
        "stored knowledge."
    ),
    return_direct=False,
    requires_api=False,
    defer_loading=False,
    keywords=[
        "remember",
        "memory",
        "recall",
        "search",
        "find",
        "know",
        "what do I know",
    ],
    input_examples=[
        {"query": "user's health conditions"},
        {"query": "what projects is the user working on"},
        {"query": "user's name and location"},
        {"query": "user's hobbies"},
    ],
)
def recall_knowledge(
    query: Annotated[str, "What you're trying to remember or find"],
    max_results: Annotated[int, "Maximum facts to return"] = 5,
    api: Any = None,
) -> str:
    """Search the knowledge base for relevant facts.

    Uses semantic search to find facts matching the query across all
    stored knowledge files.

    Args:
        query: What to search for.
        max_results: Max results to return.
        api: API instance (injected).

    """
    try:
        from airunner_services.knowledge import get_knowledge_base

        kb = get_knowledge_base()

        agent = api if api and hasattr(api, "search") else None
        rag_results = kb.search_rag(query, k=max_results, agent=agent)
        keyword_results = kb.search(query, max_results=max_results)
        tfidf_results = kb.search_tfidf(query, max_results=max_results)

        results = merge_search_results(
            rag_results, keyword_results, tfidf_results
        )

        if not results:
            return (
                f"No knowledge found for: '{query}'.\n\n"
                "**ACTION REQUIRED:** You MUST now use "
                "search_news or search_web to find this "
                "information. Do NOT tell the user to search "
                "elsewhere - use the tools available to you."
            )

        return "\n".join(f"- {fact}" for fact in results[:max_results])

    except Exception as e:
        logger.error(f"Error recalling knowledge: {e}")
        return f"Error: {str(e)}"
