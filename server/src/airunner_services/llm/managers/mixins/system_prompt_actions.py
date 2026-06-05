"""Action-specific system prompt helpers."""

from __future__ import annotations

from typing import List, Optional

from airunner_services.contract_enums import LLMActionType
from airunner_services.llm.managers.mixins.system_prompt_action_text import (
    ACTION_MODE_PROMPTS,
    FORCE_TOOL_INSTRUCTIONS,
    SEARCH_WEB_FORCE_PROMPT,
    START_WORKFLOW_FORCE_PROMPT,
)
from airunner_services.llm.managers.mixins.system_prompt_context import (
    build_research_mode_prompt,
    build_system_prompt_for_action,
    get_prompt_mode,
)
from airunner_services.llm.managers.mixins.system_prompt_text import (
    MATH_SYSTEM_PROMPT,
    PRECISION_SYSTEM_PROMPT,
)


def get_system_prompt_with_context(
    owner,
    action: LLMActionType,
    tool_categories: Optional[List] = None,
    force_tool: Optional[str] = None,
) -> str:
    """Return the system prompt selected for the active tool context."""
    mode = get_prompt_mode(tool_categories)
    if mode == "math":
        base_prompt = MATH_SYSTEM_PROMPT
    elif mode == "precision":
        base_prompt = PRECISION_SYSTEM_PROMPT
    else:
        base_prompt = get_system_prompt_for_action(owner, action, force_tool)
    if force_tool and mode != "conversational":
        return base_prompt + get_force_tool_instruction(force_tool)
    return base_prompt


def get_system_prompt_for_action(
    owner,
    action: LLMActionType,
    force_tool: Optional[str] = None,
) -> str:
    """Return the final action-specific system prompt."""
    if force_tool == "search_web":
        return build_research_mode_prompt(owner) + get_force_tool_instruction(
            force_tool
        )
    base_prompt = build_system_prompt_for_action(owner, action)
    if force_tool:
        return base_prompt + get_force_tool_instruction(force_tool)
    return base_prompt + ACTION_MODE_PROMPTS.get(action, "")


def get_force_tool_instruction(tool_name: str) -> str:
    """Return the instruction block that forces one specific tool."""
    if tool_name == "start_workflow":
        return START_WORKFLOW_FORCE_PROMPT
    if tool_name == "search_web":
        return SEARCH_WEB_FORCE_PROMPT
    instruction = FORCE_TOOL_INSTRUCTIONS.get(
        tool_name,
        "Use this tool to help with the user's request.",
    )
    return (
        f"\n\n**FORCED TOOL MODE**"
        f"\nYou MUST use the `{tool_name}` tool to respond to this request."
        f"\n\n**Instructions:** {instruction}"
        f"\n\n**CRITICAL RULES:**"
        f"\n1. Your FIRST action MUST be to call `{tool_name}`"
        f"\n2. Do NOT skip the tool call or try to answer without it"
        f"\n3. After the tool returns results, provide a helpful response based on those results"
        f"\n4. If the tool fails, explain what went wrong"
    )