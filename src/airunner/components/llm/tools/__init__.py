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
from airunner.components.llm.tools.project_operations_handler import (
    ProjectOperationsHandler,
)
from airunner.components.llm.tools.project_generated_write_review_handler import (
    ProjectGeneratedWriteReviewHandler,
)
from airunner.components.llm.tools.project_runtime_tools_handler import (
    ProjectRuntimeToolsHandler,
)
from airunner.components.llm.tools.project_tool_result import (
    ProjectToolResult,
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
    research_tools,
    research_document_tools,  # CRITICAL: Document creation tools for Deep Research
    research_validation_tools,  # URL, content, and temporal validation for research
    research_rag_tools,  # RAG-based research tools (search, summaries)
    qa_tools,
    # Phase 3: Code generation tools
    code_generation_tools,
    project_file_tools,
    project_runtime_tools,
    # Document editor tools for interactive code/document editing
    document_editor_tools,
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
    "ProjectGeneratedWriteReviewHandler",
    "ProjectOperationsHandler",
    "ProjectRuntimeToolsHandler",
    "ProjectToolResult",
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
    "research_tools",
    "research_validation_tools",
    "qa_tools",
    "project_file_tools",
    "project_runtime_tools",
    # Document editor tools
    "document_editor_tools",
    # Long-running project tools
    "project_tools",
]
