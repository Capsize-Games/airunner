"""Central module for loading all LLM tools.

Import this module to register all available tools with the ToolRegistry.
"""

# Generic code validation helpers
from airunner.components.llm.tools.code_validator import (
    CodeValidator,
    ValidationResult,
    ValidationIssue,
)
from airunner.components.llm.tools.test_runner import (
    TestRunner,
    TestResult,
)

# Import all tool modules to trigger registration
from airunner.components.llm.tools import (
    image_tools,
    system_tools,
    conversation_tools,
    math_tools,
    reasoning_tools,
    web_tools,
    rag_tools,
    knowledge_tools,
    user_data_tools,
    agent_tools,
    mood_tools,
    generation_tools,  # Direct text generation tools
    # Phase 2: Mode-specific tools
    author_tools,
    code_tools,
    research_validation_tools,  # URL, content, and temporal validation for research
    research_rag_tools,  # RAG-based research tools (search, summaries)
    qa_tools,
)

# Long-running project management tools
from airunner.components.llm.long_running import tools as project_tools

# Load explicitly enabled external extensions.
# Extensions register tools via the same ToolRegistry and can override by name.
try:
    from airunner.components.llm.core.extensions_loader import load_extensions

    load_extensions(force_reload=False)
except Exception:
    # Extensions are optional and must never break tool import.
    pass

__all__ = [
    # Generic code validation helpers
    "CodeValidator",
    "ValidationResult",
    "ValidationIssue",
    "TestRunner",
    "TestResult",
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
    "agent_tools",
    "mood_tools",
    "generation_tools",
    # Phase 2: Mode-specific tools
    "author_tools",
    "code_tools",
    "research_validation_tools",
    "qa_tools",
    # Long-running project tools
    "project_tools",
]
