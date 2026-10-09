"""Chatbot-scoped companion memory tools (release B05).

Five tools with frozen schemas (names, parameters, and citation
format are stable from this issue on; additive-only changes):

- ``record_companion_fact(chatbot_id, fact, subject, source)``
- ``recall_companion_facts(chatbot_id, query, max_results)``
- ``update_companion_fact(chatbot_id, fact_id, content)``
- ``retract_companion_fact(chatbot_id, fact_id, reason)``
- ``recall_companion_turns(chatbot_id, session_id, query,
  max_results)``

``chatbot_id`` is required on every tool; scope is enforced in the
repository, never inferred from prompt text. Replies carry source
citations (``[fact:7]`` / ``[turn:12]``). Vector ranking engages
per chatbot once its B04 index is bound via ``bind_chatbot_index``.
"""

from typing import Annotated, Any

from airunner_services.llm.companion.recall import (
    bind_chatbot_index,
    bound_chatbot_ids,
    default_repository,
    get_bound_index,
    unbind_all_chatbot_indexes,
    unbind_chatbot_index,
)
from airunner_services.llm.core.tool_registry import ToolCategory, tool


def get_companion_repository() -> Any:
    """Return the scoped companion memory repository."""
    return default_repository()


def _recall_context(chatbot_id: int) -> Any:
    """Return (repository, index, client) for one chatbot."""
    index, client = get_bound_index(chatbot_id)
    return get_companion_repository(), index, client


@tool(
    name="record_companion_fact",
    category=ToolCategory.KNOWLEDGE,
    description=(
        "Record one fact for one chatbot's scoped memory. Returns the "
        "stored fact with its source citation."
    ),
    return_direct=False,
    requires_api=False,
    keywords=["remember", "memory", "fact", "store", "save", "record"],
    input_examples=[
        {"chatbot_id": 7, "fact": "the library lends telescopes"},
    ],
)
def record_companion_fact(
    chatbot_id: Annotated[int, "Owning chatbot ID (scope, required)"],
    fact: Annotated[str, "The factual statement to remember"],
    subject: Annotated[str, "Short subject label"] = "",
    source: Annotated[str, "Provenance label"] = "companion-tool",
) -> str:
    """Record one scoped fact; returns its citation."""
    from airunner_services.llm.companion import fact_recall
    from airunner_services.llm.companion import recall as shared

    try:
        repo, index, client = _recall_context(chatbot_id)
        stored = fact_recall.record_fact(
            repo,
            chatbot_id,
            fact,
            subject=subject or None,
            source=source,
            index=index,
            client=client,
        )
        cite = shared.fact_citation(stored.fact_id)
        return f"Recorded {cite}: {stored.content}"
    except Exception as exc:
        return f"Error: {exc}"


@tool(
    name="recall_companion_facts",
    category=ToolCategory.KNOWLEDGE,
    description=(
        "Recall one chatbot's scoped facts ranked for a query. Every "
        "hit carries its source citation."
    ),
    return_direct=False,
    requires_api=False,
    keywords=["recall", "remember", "memory", "search", "find", "fact"],
    input_examples=[
        {"chatbot_id": 7, "query": "library telescopes"},
    ],
)
def recall_companion_facts(
    chatbot_id: Annotated[int, "Owning chatbot ID (scope, required)"],
    query: Annotated[str, "What to remember or find"],
    max_results: Annotated[int, "Maximum facts to return"] = 5,
) -> str:
    """Recall scoped facts; every hit carries its citation."""
    from airunner_services.llm.companion import fact_recall
    from airunner_services.llm.companion import recall as shared

    try:
        repo, index, client = _recall_context(chatbot_id)
        facts = fact_recall.recall_facts(
            repo,
            chatbot_id,
            query,
            limit=max_results,
            index=index,
            client=client,
        )
        return shared.format_cited_facts(facts, query=query)
    except Exception as exc:
        return f"Error: {exc}"


@tool(
    name="update_companion_fact",
    category=ToolCategory.KNOWLEDGE,
    description="Replace one chatbot's fact content by fact ID.",
    return_direct=False,
    requires_api=False,
    keywords=["update", "change", "modify", "edit", "fix", "correct"],
    input_examples=[
        {"chatbot_id": 7, "fact_id": 3, "content": "the library opens late"},
    ],
)
def update_companion_fact(
    chatbot_id: Annotated[int, "Owning chatbot ID (scope, required)"],
    fact_id: Annotated[int, "Fact ID to update (see its citation)"],
    content: Annotated[str, "Replacement content"],
) -> str:
    """Replace one scoped fact's content, keeping its citation."""
    from airunner_services.llm.companion import fact_recall
    from airunner_services.llm.companion import recall as shared

    try:
        stored = fact_recall.update_fact(
            get_companion_repository(), chatbot_id, fact_id, content
        )
        cite = shared.fact_citation(stored.fact_id)
        return f"Updated {cite}: {stored.content}"
    except Exception as exc:
        return f"Error: {exc}"


@tool(
    name="retract_companion_fact",
    category=ToolCategory.KNOWLEDGE,
    description=(
        "Retract one chatbot's fact by fact ID. The row is kept and "
        "stays recoverable; it is excluded from recall."
    ),
    return_direct=False,
    requires_api=False,
    keywords=["retract", "remove", "forget", "withdraw", "delete"],
    input_examples=[
        {"chatbot_id": 7, "fact_id": 3, "reason": "superseded"},
    ],
)
def retract_companion_fact(
    chatbot_id: Annotated[int, "Owning chatbot ID (scope, required)"],
    fact_id: Annotated[int, "Fact ID to retract (see its citation)"],
    reason: Annotated[str, "Why the fact is withdrawn"] = "",
) -> str:
    """Retract one scoped fact without deleting it."""
    from airunner_services.llm.companion import fact_recall
    from airunner_services.llm.companion import recall as shared

    try:
        stored = fact_recall.retract_fact(
            get_companion_repository(),
            chatbot_id,
            fact_id,
            reason=reason or None,
        )
        cite = shared.fact_citation(stored.fact_id)
        return f"Retracted {cite} (recoverable, not deleted)"
    except Exception as exc:
        return f"Error: {exc}"


@tool(
    name="recall_companion_turns",
    category=ToolCategory.CONVERSATION,
    description=(
        "Recall one chatbot session's past turns, optionally ranked "
        "for a query. Every turn carries its source citation."
    ),
    return_direct=False,
    requires_api=False,
    keywords=["recall", "turns", "history", "conversation", "said", "past"],
    input_examples=[
        {"chatbot_id": 7, "session_id": 9, "query": "telescope"},
    ],
)
def recall_companion_turns(
    chatbot_id: Annotated[int, "Owning chatbot ID (scope, required)"],
    session_id: Annotated[int, "Session ID to recall from"],
    query: Annotated[str, "Optional query to rank turns by"] = "",
    max_results: Annotated[int, "Maximum turns to return"] = 5,
) -> str:
    """Recall one session's past turns, cited."""
    from airunner_services.llm.companion import recall as shared
    from airunner_services.llm.companion import turn_recall

    try:
        repo, index, client = _recall_context(chatbot_id)
        turns = turn_recall.recall_turns(
            repo,
            chatbot_id,
            session_id,
            query=query,
            limit=max_results,
            index=index,
            client=client,
        )
        return shared.format_cited_turns(turns, query=query)
    except Exception as exc:
        return f"Error: {exc}"


__all__ = [
    "bind_chatbot_index",
    "bound_chatbot_ids",
    "get_bound_index",
    "get_companion_repository",
    "recall_companion_facts",
    "recall_companion_turns",
    "record_companion_fact",
    "retract_companion_fact",
    "unbind_all_chatbot_indexes",
    "unbind_chatbot_index",
    "update_companion_fact",
]
