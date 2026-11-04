"""Central module for loading all LLM tools.

Importing this module registers every built-in tool with the
``ToolRegistry`` (each tool module registers itself on import via the
``@tool`` decorator). Long-running project tools register from
``airunner_services.llm.long_running.tools``; explicitly enabled
external extensions load last through ``extensions_loader`` and may
override a built-in by registering the same name.

Nothing here executes at import time beyond registration: validation
(``validate_tool_code``), capability confinement
(``tool_worker_confine``), and per-request server-side argument checks
(``ToolExecutionMixin``) all run later, on the tool-call path.
"""

# Import all tool modules to trigger registration
from airunner_services.llm.tools import (
    image_tools,
    system_tools,
    conversation_tools,
    math_tools,
    reasoning_tools,
    rag_tools,
    knowledge_tools,
    user_data_tools,
    mood_tools,
    generation_tools,  # Direct text generation tools
    # Phase 2: Mode-specific tools
    author_tools,
    research_validation_tools,  # URL, content, and temporal validation for research
    research_rag_tools,  # RAG-based research tools (search, summaries)
    qa_tools,
    companion_memory_tools,  # Scoped companion recall (B05)
)
from airunner_services.tools import web_tools

# Long-running project management tools
from airunner_services.llm.long_running import tools as project_tools

# Load explicitly enabled external extensions.
# Extensions register tools via the same ToolRegistry and can override by name.
try:
    from airunner_services.llm.core.extensions_loader import load_extensions

    load_extensions(force_reload=False)
except Exception:
    # Extensions are optional and must never break tool import.
    pass

__all__ = [
    # Tool modules
    "image_tools",
    "system_tools",
    "conversation_tools",
    "math_tools",
    "reasoning_tools",
    "web_tools",
    "rag_tools",
    "knowledge_tools",
    "user_data_tools",
    "mood_tools",
    "generation_tools",
    # Phase 2: Mode-specific tools
    "author_tools",
    "research_validation_tools",
    "qa_tools",
    "companion_memory_tools",
    # Long-running project tools
    "project_tools",
]
