"""Structured GPT-OSS-style channels for persisted messages."""

from enum import Enum


class AgentMessageChannel(str, Enum):
    """Supported channels for agent run transcripts."""

    ANALYSIS = "analysis"
    COMMENTARY = "commentary"
    FINAL = "final"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
