"""Workflow setup helpers for generation."""

from __future__ import annotations

from typing import Any, Dict, Optional

from airunner_services.contract_enums import LLMActionType
from airunner_services.llm.managers.request_preparation import (
    WorkflowRequestSetup,
    build_workflow_request_setup,
)


def sync_request_scope_to_workflow_manager(owner) -> None:
    """Propagate the active request ID to workflow-scoped emitters."""
    if not owner._workflow_manager:
        return
    request_id = getattr(owner, "_current_request_id", None)
    setattr(
        owner._workflow_manager,
        "llm_request",
        getattr(owner, "llm_request", None),
    )
    if hasattr(owner._workflow_manager, "set_request_id"):
        owner._workflow_manager.set_request_id(request_id)
        return
    setattr(owner._workflow_manager, "_current_request_id", request_id)


def clamp_generation_tokens(owner, generation_kwargs: Dict[str, Any]) -> None:
    """Clamp max_new_tokens to the loaded model context length."""
    target_ctx = getattr(owner, "_target_context_length", None)
    requested = generation_kwargs.get("max_new_tokens")
    if not target_ctx or requested is None:
        return
    if requested > target_ctx:
        owner.logger.info(
            "Clamping max_new_tokens from %s to target context %s",
            requested,
            target_ctx,
        )
        generation_kwargs["max_new_tokens"] = target_ctx


def setup_generation_workflow(
    owner,
    action: LLMActionType,
    system_prompt: Optional[str],
    skip_tool_setup: bool = False,
    llm_request: Optional[Any] = None,
) -> str:
    """Configure workflow prompts and tools for one generation request."""
    request_setup = build_workflow_request_setup(llm_request)
    if system_prompt:
        action_system_prompt = owner._augment_custom_system_prompt(
            base_prompt=system_prompt,
            action=action,
            include_mood=request_setup.include_mood,
            include_datetime=request_setup.include_datetime,
            include_style=request_setup.include_style,
            include_memory=request_setup.include_memory,
            include_ui_context=request_setup.include_ui_context,
        )
    else:
        action_system_prompt = owner.get_system_prompt_with_context(
            action,
            request_setup.tool_categories,
            request_setup.force_tool,
        )
    apply_workflow_request_setup(
        owner,
        action,
        action_system_prompt,
        skip_tool_setup,
        request_setup,
    )
    return action_system_prompt


def apply_workflow_request_setup(
    owner,
    action: LLMActionType,
    action_system_prompt: str,
    skip_tool_setup: bool,
    request_setup: WorkflowRequestSetup,
) -> None:
    """Apply one request's workflow settings to the active manager."""
    if not owner._workflow_manager:
        return
    owner._workflow_manager.update_system_prompt(action_system_prompt)
    set_workflow_force_tool(owner, request_setup.force_tool)
    set_workflow_response_format(owner, request_setup.response_format)
    update_workflow_tools_for_action(owner, action, skip_tool_setup)


def set_workflow_force_tool(owner, force_tool: Optional[str]) -> None:
    """Synchronize the request force-tool state into the workflow."""
    if not hasattr(owner._workflow_manager, "set_force_tool"):
        return
    owner._workflow_manager.set_force_tool(force_tool)
    owner.logger.info("Set workflow force_tool to: %s", force_tool)


def set_workflow_response_format(
    owner,
    response_format: Optional[str],
) -> None:
    """Apply one request response-format override when present."""
    if not response_format:
        return
    if not hasattr(owner._workflow_manager, "set_response_format"):
        return
    owner._workflow_manager.set_response_format(response_format)
    owner.logger.info("Set workflow response format to: %s", response_format)


def update_workflow_tools_for_action(
    owner,
    action: LLMActionType,
    skip_tool_setup: bool,
) -> None:
    """Refresh action tools unless request-time filtering already ran."""
    if skip_tool_setup:
        owner.logger.info(
            "Skipping tool setup - tools already filtered by tool_categories"
        )
        return
    if not owner._tool_manager:
        return
    action_tools = owner._tool_manager.get_tools_for_action(action)
    owner._workflow_manager.update_tools(action_tools)
