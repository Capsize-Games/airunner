"""Long-running agent harness module.

This module implements Anthropic's two-phase approach for long-running agents:
1. Initializer Agent - Sets up project structure, feature lists, progress tracking
2. Session Agent - Makes incremental progress on one feature at a time

Key improvements over basic implementation:
- Sub-agent delegation for specialized tasks
- Decision memory for tracking past outcomes
- Sophisticated state recovery
- Integration with AI Runner's existing tool system

Reference: https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents

Usage:
    ```python
    from airunner.components.llm.long_running import LongRunningHarness

    # Create harness with your LLM
    harness = LongRunningHarness(
        chat_model=your_llm,
        tools=your_tools,
    )

    # Create a project
    project_id = harness.create_project(
        name="My App",
        description="Build a chat application with real-time messaging",
        working_directory="/path/to/project"
    )

    # Run sessions until complete
    result = harness.run_until_complete(project_id, max_sessions=50)
    ```
"""

from airunner.components.llm.long_running.data.project_state import (
    ProjectState,
    ProjectFeature,
    ProgressEntry,
    SessionState,
    DecisionMemory,
    ProjectStatus,
    FeatureStatus,
    FeatureCategory,
    DecisionOutcome,
)
from airunner.components.llm.long_running.project_manager import ProjectManager
from airunner.components.llm.long_running.initializer_agent import (
    InitializerAgent,
)
from airunner.components.llm.long_running.session_agent import SessionAgent
from airunner.components.llm.long_running.harness import LongRunningHarness
from airunner.components.llm.long_running.sub_agents import (
    BaseSubAgent,
    CodeSubAgent,
    ResearchSubAgent,
    TestingSubAgent,
    DocumentationSubAgent,
    create_sub_agents,
)
from airunner.components.llm.long_running.tools import LONG_RUNNING_TOOLS
from airunner.components.llm.long_running.task_detector import (
    TaskType,
    TaskAnalysis,
    analyze_task,
    should_use_harness,
)
from airunner.components.llm.long_running.auto_wrapper import (
    AutoHarnessWrapper,
    create_auto_wrapper,
)

__all__ = [
    # Data models
    "ProjectState",
    "ProjectFeature",
    "ProgressEntry",
    "SessionState",
    "DecisionMemory",
    "ProjectStatus",
    "FeatureStatus",
    "FeatureCategory",
    "DecisionOutcome",
    # Core components
    "ProjectManager",
    "InitializerAgent",
    "SessionAgent",
    "LongRunningHarness",
    # Sub-agents
    "BaseSubAgent",
    "CodeSubAgent",
    "ResearchSubAgent",
    "TestingSubAgent",
    "DocumentationSubAgent",
    "create_sub_agents",
    # Auto-wrapping
    "TaskType",
    "TaskAnalysis",
    "analyze_task",
    "should_use_harness",
    "AutoHarnessWrapper",
    "create_auto_wrapper",
    # Tools
    "LONG_RUNNING_TOOLS",
]
