"""Visible request modes for the AIRunner chat footer."""

from dataclasses import dataclass

from airunner.enums import LLMActionType


@dataclass(frozen=True)
class ChatRequestMode:
    """Describe one request mode exposed in the chat footer."""

    key: str
    label: str
    action: LLMActionType
    use_mode_routing: bool
    mode_override: str | None
    prompt_prefix: str
    tooltip: str


REQUEST_MODES = (
    ChatRequestMode(
        key="ask",
        label="Ask",
        action=LLMActionType.CHAT,
        use_mode_routing=False,
        mode_override=None,
        prompt_prefix="",
        tooltip=(
            "Normal chat and Q&A. Does not force the coding workflow."
        ),
    ),
    ChatRequestMode(
        key="plan",
        label="Plan",
        action=LLMActionType.CODE,
        use_mode_routing=True,
        mode_override="code",
        prompt_prefix=(
            "Plan this coding task before implementation. Return a concise "
            "step-by-step plan, the files to touch, and tests to add. "
            "Do not edit files or run commands yet.\n\nTask: "
        ),
        tooltip=(
            "Planning mode. Build an implementation plan without "
            "modifying the workspace."
        ),
    ),
    ChatRequestMode(
        key="agent",
        label="Agent",
        action=LLMActionType.CODE,
        use_mode_routing=True,
        mode_override="code",
        prompt_prefix=(
            "Solve this as an active coding task in the current workspace. "
            "Use tools, inspect files, edit code, and run validations when "
            "they help.\n\nTask: "
        ),
        tooltip=(
            "Coding agent mode. Use workspace tools and code workflows for "
            "implementation tasks."
        ),
    ),
)


def chat_request_modes() -> tuple[ChatRequestMode, ...]:
    """Return the request modes shown in the chat footer."""

    return REQUEST_MODES


def get_chat_request_mode(key: str | None) -> ChatRequestMode:
    """Return one request mode, falling back to Ask."""

    for mode in REQUEST_MODES:
        if mode.key == key:
            return mode
    return REQUEST_MODES[0]
