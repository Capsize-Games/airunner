"""LLM agent subgraphs and workflow management for specialized modes.

This package provides:
- Specialized agents: AuthorAgent, CodeAgent, ResearchAgent, QAAgent
- WorkflowState: State machine for tracking multi-phase execution
- Workflow tools: Tools for LLM to manage its own workflow
- Workflow prompts: System prompts teaching workflow execution
"""

from airunner.components.llm.agents.author_agent import AuthorAgent
from airunner.components.llm.agents.code_agent import CodeAgent
from airunner.components.llm.agents.research_agent import ResearchAgent
from airunner.components.llm.agents.qa_agent import QAAgent

from airunner.components.llm.agents.workflow_state import (
    Phase,
    TodoItem,
    TodoStatus,
    WorkflowDefinition,
    WorkflowState,
    WorkflowType,
    WORKFLOW_REGISTRY,
    get_workflow,
    create_dynamic_workflow,
)

from airunner.components.llm.agents.workflow_tools import (
    WORKFLOW_TOOLS,
    get_current_state,
    set_current_state,
    reset_workflow_state,
    is_workflow_active,
    require_workflow,
    require_execution_phase,
)

from airunner.components.llm.agents.workflow_prompts import (
    WORKFLOW_SYSTEM_PROMPT,
    CODING_WORKFLOW_PROMPT,
    RESEARCH_WORKFLOW_PROMPT,
    get_workflow_prompt,
)

__all__ = [
    # Agents
    "AuthorAgent",
    "CodeAgent",
    "ResearchAgent",
    "QAAgent",
    # Workflow State
    "Phase",
    "TodoItem",
    "TodoStatus",
    "WorkflowDefinition",
    "WorkflowState",
    "WorkflowType",
    "WORKFLOW_REGISTRY",
    "get_workflow",
    "create_dynamic_workflow",
    # Workflow Tools
    "WORKFLOW_TOOLS",
    "get_current_state",
    "set_current_state",
    "reset_workflow_state",
    "is_workflow_active",
    "require_workflow",
    "require_execution_phase",
    # Workflow Prompts
    "WORKFLOW_SYSTEM_PROMPT",
    "CODING_WORKFLOW_PROMPT",
    "RESEARCH_WORKFLOW_PROMPT",
    "get_workflow_prompt",
]
