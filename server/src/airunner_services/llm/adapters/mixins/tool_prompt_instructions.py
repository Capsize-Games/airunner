"""Prompt-instruction helpers for manual tool calling."""

INSTRUCTION_HEADER = "## IMPORTANT: Tool Usage Instructions\n\n"
INSTRUCTION_INTRO = "You have access to the following tools to help users:\n\n"
INSTRUCTION_USAGE = (
    "\n\n**How to use a tool:**\n\n"
    "When you need to use a tool, respond with ONLY a JSON code block "
    "in this format:\n\n"
    '```json\n{\n    "tool": "tool_name",\n'
    '    "arguments": {\n        "param_name": "value"\n'
    "    }\n}\n```\n\n"
)
INSTRUCTION_EXAMPLE = (
    '**Example:** If user asks "generate an image of a sunset", '
    "respond:\n"
    '```json\n{\n    "tool": "generate_image",\n'
    '    "arguments": {\n'
    '        "prompt": "sunset over ocean with orange and pink sky"\n'
    "    }\n}\n```\n\n"
)
INSTRUCTION_TAIL = (
    "Do NOT add any other text when calling a tool - just the JSON "
    "block. After the tool executes, you will receive the result and "
    "can then provide a response to the user."
)


def build_tool_instructions(tools_text: str) -> str:
    """Return manual tool-calling instructions for system prompts."""
    return (
        INSTRUCTION_HEADER
        + INSTRUCTION_INTRO
        + tools_text
        + INSTRUCTION_USAGE
        + INSTRUCTION_EXAMPLE
        + INSTRUCTION_TAIL
    )
