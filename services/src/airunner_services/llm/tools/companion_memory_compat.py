"""Compatibility adapter: legacy memory tools onto scoped recall (B05).

The pre-companion tools stay registered and keep working against
their own stores; this module documents, per legacy name, which
scoped companion tool replaces it and adapts the call shape:

==========================  =========================  ================
Legacy tool                 Scoped replacement          Notes
==========================  =========================  ================
``record_knowledge``        ``record_companion_fact``  ``section`` maps
                                                   to the fact subject
``recall_knowledge``        ``recall_companion_facts`` replies gain
                                                   ``[fact:N]`` cites
``update_knowledge``        ``update_companion_fact``  find-text resolves
                                                   to one cited fact
``delete_knowledge``        ``retract_companion_fact`` retract, not
                                                   delete (recoverable)
``read_knowledge_file``     ``recall_companion_facts`` empty query lists
                                                   recent facts, cited
``get_conversation_summary`` ``recall_companion_turns`` cited turns, not
                                                   an agent summary
``load_conversation``       ``recall_companion_turns`` scoped by chatbot
                                                   plus session
==========================  =========================  ================

Intentionally unmapped (no scoped equivalent; the legacy tools
remain the only path): ``list_knowledge_files`` (daily markdown
files do not exist in the SQLite store), ``clear_chat_history``
(agent-local, not persisted memory), ``store_user_data`` /
``get_user_data`` (the ``User`` profile row, not chatbot memory).

Every adapter takes ``chatbot_id`` first: scope is explicit, never
inferred from prompt text.
"""

from typing import Any, Callable, Dict, List

LEGACY_TOOL_MAP: Dict[str, str] = {
    "record_knowledge": "record_companion_fact",
    "recall_knowledge": "recall_companion_facts",
    "update_knowledge": "update_companion_fact",
    "delete_knowledge": "retract_companion_fact",
    "read_knowledge_file": "recall_companion_facts",
    "get_conversation_summary": "recall_companion_turns",
    "load_conversation": "recall_companion_turns",
}

UNMAPPED_LEGACY_TOOLS: List[str] = [
    "list_knowledge_files",
    "clear_chat_history",
    "store_user_data",
    "get_user_data",
]


def legacy_tool_names() -> List[str]:
    """Return the legacy tool names this adapter covers."""
    return sorted(LEGACY_TOOL_MAP)


def resolve_legacy_tool(legacy_name: str) -> str:
    """Return the scoped replacement for one legacy tool name."""
    return LEGACY_TOOL_MAP[legacy_name]


def record_knowledge_scoped(
    chatbot_id: int, fact: str, section: str = "Notes"
) -> str:
    """Legacy ``record_knowledge`` against scoped memory."""
    from airunner_services.llm.tools import companion_memory_tools as tools

    return tools.record_companion_fact(
        chatbot_id, fact, subject=section, source="legacy-adapter"
    )


def recall_knowledge_scoped(
    chatbot_id: int, query: str, max_results: int = 5
) -> str:
    """Legacy ``recall_knowledge`` against scoped memory."""
    from airunner_services.llm.tools import companion_memory_tools as tools

    return tools.recall_companion_facts(chatbot_id, query, max_results)


def update_knowledge_scoped(
    chatbot_id: int, find_text: str, replace_text: str
) -> str:
    """Legacy find/replace update resolved to one cited fact."""
    from airunner_services.llm.companion import fact_recall
    from airunner_services.llm.tools import companion_memory_tools as tools

    facts = fact_recall.recall_facts(
        tools.get_companion_repository(), chatbot_id, find_text, limit=25
    )
    for fact in facts:
        if find_text in fact.content:
            return tools.update_companion_fact(
                chatbot_id,
                fact.fact_id,
                fact.content.replace(find_text, replace_text),
            )
    return f"Text not found: '{find_text}'"


def delete_knowledge_scoped(chatbot_id: int, text: str) -> str:
    """Legacy delete as scoped retract (recoverable, never a wipe)."""
    from airunner_services.llm.companion import fact_recall
    from airunner_services.llm.companion import recall as shared
    from airunner_services.llm.tools import companion_memory_tools as tools

    facts = fact_recall.recall_facts(
        tools.get_companion_repository(), chatbot_id, text, limit=25
    )
    matched = [fact for fact in facts if text in fact.content]
    for fact in matched:
        tools.retract_companion_fact(
            chatbot_id, fact.fact_id, reason="legacy-adapter-delete"
        )
    if not matched:
        return f"Text not found: '{text}'"
    cites = " ".join(shared.fact_citation(fact.fact_id) for fact in matched)
    return f"Retracted {len(matched)} fact(s) (recoverable): {cites}"


def read_knowledge_scoped(chatbot_id: int, max_results: int = 5) -> str:
    """Legacy knowledge-file read as recent cited facts."""
    from airunner_services.llm.tools import companion_memory_tools as tools

    return tools.recall_companion_facts(chatbot_id, "", max_results)


def conversation_summary_scoped(
    chatbot_id: int, session_id: int, max_results: int = 5
) -> str:
    """Legacy conversation summary as cited past turns."""
    from airunner_services.llm.tools import companion_memory_tools as tools

    return tools.recall_companion_turns(
        chatbot_id, session_id, "", max_results
    )


def load_conversation_scoped(
    chatbot_id: int, session_id: int, max_results: int = 5
) -> str:
    """Legacy conversation load as cited past turns."""
    from airunner_services.llm.tools import companion_memory_tools as tools

    return tools.recall_companion_turns(
        chatbot_id, session_id, "", max_results
    )


LEGACY_ADAPTERS: Dict[str, Callable[..., str]] = {
    "record_knowledge": record_knowledge_scoped,
    "recall_knowledge": recall_knowledge_scoped,
    "update_knowledge": update_knowledge_scoped,
    "delete_knowledge": delete_knowledge_scoped,
    "read_knowledge_file": read_knowledge_scoped,
    "get_conversation_summary": conversation_summary_scoped,
    "load_conversation": load_conversation_scoped,
}


def adapt_legacy_tool(legacy_name: str, *args: Any, **kwargs: Any) -> str:
    """Run one legacy-named operation against scoped memory."""
    return LEGACY_ADAPTERS[legacy_name](*args, **kwargs)


__all__ = [
    "LEGACY_ADAPTERS",
    "LEGACY_TOOL_MAP",
    "UNMAPPED_LEGACY_TOOLS",
    "adapt_legacy_tool",
    "conversation_summary_scoped",
    "delete_knowledge_scoped",
    "legacy_tool_names",
    "load_conversation_scoped",
    "read_knowledge_scoped",
    "recall_knowledge_scoped",
    "record_knowledge_scoped",
    "resolve_legacy_tool",
    "update_knowledge_scoped",
]
