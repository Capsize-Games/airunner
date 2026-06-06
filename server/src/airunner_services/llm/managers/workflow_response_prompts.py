"""Prompt builders for workflow continuation and forced responses."""

from __future__ import annotations

DEFAULT_WORKFLOW_NEXT_ACTION = (
    "Call transition_phase('planning', " "'Simple task, moving to planning')"
)


def extract_next_workflow_action(tool_content: str) -> str:
    """Return the next workflow action encoded in tool output."""
    if not tool_content:
        return ""

    next_call_marker = "YOUR NEXT TOOL CALL:"
    immediate_action_marker = "IMMEDIATE NEXT ACTION"
    immediate_call_marker = "Call this tool NOW:"

    if next_call_marker in tool_content:
        for line in tool_content.splitlines():
            if next_call_marker in line:
                return line.split(next_call_marker, maxsplit=1)[-1].strip()

    if immediate_action_marker in tool_content:
        lines = tool_content.splitlines()
        for index, line in enumerate(lines):
            if immediate_call_marker in line and index + 1 < len(lines):
                return lines[index + 1].strip()

    return ""


def build_workflow_correction_prompt(
    tool_name: str,
    user_question: str,
    next_action: str,
) -> str:
    """Return the duplicate-workflow correction prompt."""
    action_line = (
        f"REQUIRED: Call {next_action}"
        if next_action
        else DEFAULT_WORKFLOW_NEXT_ACTION
    )
    lines = [
        (
            f"[SYSTEM CORRECTION] You called {tool_name} twice. "
            "The workflow is ALREADY ACTIVE."
        ),
        "",
        "DO NOT output any text response. DO NOT explain what you will do.",
        "You MUST call a workflow tool NOW.",
        "",
        action_line,
        "",
        f"Your task: {user_question}",
        "",
        "CALL THE TOOL NOW. NO TEXT RESPONSE.",
    ]
    return "\n".join(lines)


def build_workflow_continuation_prompt(
    tool_name: str,
    user_question: str,
    tool_content: str,
    next_action: str,
) -> str:
    """Return the prompt that nudges the model to continue a workflow."""
    next_step_line = (
        f"The next step is: {next_action}"
        if next_action
        else "Follow the instructions in the workflow status above."
    )
    lines = [
        (
            "You already started the workflow. The workflow has given you "
            "specific instructions."
        ),
        "",
        "WORKFLOW STATUS:",
        tool_content[:1500],
        "",
        (
            f"CRITICAL: You called {tool_name} twice. The workflow is "
            "already active!"
        ),
        "",
        next_step_line,
        "",
        (
            f"DO NOT call {tool_name} again. Instead, call the NEXT tool "
            "in the sequence."
        ),
        "",
        "For a structured workflow, the typical sequence is:",
        "1. start_workflow (DONE - you already did this)",
        "2. transition_phase('planning', 'reason')",
        "3. add_todo_item('title', 'description')",
        "4. transition_phase('execution', 'reason')",
        "5. start_todo_item('todo_id')",
        "6. use the task tools needed for that TODO",
        "7. complete_todo_item('todo_id')",
        "8. transition_phase('complete', 'All done')",
        "",
        f"User's original request: {user_question}",
        "",
        (
            "Now call the NEXT workflow tool to continue. Do NOT repeat "
            "start_workflow."
        ),
    ]
    return "\n".join(lines)


def build_tool_result_response_prompt(
    all_tool_content: str,
    user_question: str,
) -> str:
    """Return the synthesis prompt for a post-tool answer."""
    lines = [
        (
            "You are answering a question based on search results. "
            "Respond naturally and conversationally."
        ),
        "",
    ]
    if user_question:
        lines.extend([f"User's question: {user_question}", ""])

    lines.extend(
        [
            "Search results:",
            all_tool_content,
            "",
            (
                "Based on the search results above, provide a clear, "
                "conversational answer to the user's question."
            ),
            "Use ONLY the information from the search results.",
            "Do not call any tools, do not use JSON, just write a natural response.",
            "Avoid repetition and be concise.",
        ]
    )
    return "\n".join(lines)
