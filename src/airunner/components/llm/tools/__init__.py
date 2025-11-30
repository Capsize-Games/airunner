"""
Central module for loading all LLM tools and code generation infrastructure.

Import this module to register all available tools with the ToolRegistry.
"""

# Code generation infrastructure
from airunner.components.llm.tools.code_session import (
    CodeSession,
    CodeSessionConfig,
    CodeSessionManager,
)
from airunner.components.llm.tools.code_operations_handler import (
    CodeOperationsHandler,
    CodeOperationResult,
)
from airunner.components.llm.tools.code_validator import (
    CodeValidator,
    ValidationResult,
    ValidationIssue,
)
from airunner.components.llm.tools.code_quality_manager import (
    CodeQualityManager,
    CodeQualityResult,
)
from airunner.components.llm.tools.test_runner import (
    TestRunner,
    TestResult,
)
from airunner.components.llm.tools.multi_file_code_tool import (
    MultiFileCodeSession,
    MultiFileCodeTool,
)

# Import all tool modules to trigger registration
from airunner.components.llm.tools import (
    image_tools,
    system_tools,
    conversation_tools,
    math_tools,
    reasoning_tools,
    web_tools,
    calendar_tools,
    rag_tools,
    knowledge_tools,
    user_data_tools,
    agent_tools,
    mood_tools,
    generation_tools,  # Direct text generation tools
    # Phase 2: Mode-specific tools
    author_tools,
    code_tools,
    research_tools,
    research_document_tools,  # CRITICAL: Document creation tools for Deep Research
    research_validation_tools,  # URL, content, and temporal validation for research
    research_rag_tools,  # RAG-based research tools (search, summaries)
    qa_tools,
    # Phase 3: Code generation tools
    code_generation_tools,
    # Document editor tools for interactive code/document editing
    document_editor_tools,
)

# Long-running project management tools
from airunner.components.llm.long_running import tools as project_tools
from airunner.components.calendar.tools import (
    calendar_tools as langchain_calendar_tools,
)

__all__ = [
    # Code generation infrastructure
    "CodeSession",
    "CodeSessionConfig",
    "CodeSessionManager",
    "CodeOperationsHandler",
    "CodeOperationResult",
    "CodeValidator",
    "ValidationResult",
    "ValidationIssue",
    "CodeQualityManager",
    "CodeQualityResult",
    "TestRunner",
    "TestResult",
    "MultiFileCodeSession",
    "MultiFileCodeTool",
    # Tool modules
    "image_tools",
    "system_tools",
    "conversation_tools",
    "math_tools",
    "reasoning_tools",
    "web_tools",
    "calendar_tools",
    "rag_tools",
    "knowledge_tools",
    "user_data_tools",
    "agent_tools",
    "mood_tools",
    "generation_tools",
    "langchain_calendar_tools",
    # Phase 2: Mode-specific tools
    "author_tools",
    "code_tools",
    "research_tools",
    "research_validation_tools",
    "qa_tools",
    # Document editor tools
    "document_editor_tools",
    # Long-running project tools
    "project_tools",
]
