"""Workflow state and workflow-tool helpers for structured execution.

This package provides:
- WorkflowState: State machine for tracking multi-phase execution
- Workflow tools: Tools for LLM to manage its own workflow
- Workflow prompts: System prompts teaching workflow execution
"""

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
    RESEARCH_WORKFLOW_PROMPT,
    get_workflow_prompt,
)

__all__ = [
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
    "RESEARCH_WORKFLOW_PROMPT",
    "get_workflow_prompt",
]
