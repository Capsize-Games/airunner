"""Shared streaming state for node response helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from langchain_core.messages import BaseMessage


@dataclass
class StreamingState:
    """Track one streamed workflow response."""

    streamed_content: List[str] = field(default_factory=list)
    collected_tool_calls: List = field(default_factory=list)
    thinking_content: List[str] = field(default_factory=list)
    tool_call_tag_buffer: List[str] = field(default_factory=list)
    json_buffer: List[str] = field(default_factory=list)
    last_chunk_message: Optional[BaseMessage] = None
    final_thinking_content: Optional[str] = None
    thinking_tag_format: str = ""
    in_thinking_block: bool = False
    thinking_started: bool = False
    using_reasoning_deltas: bool = False
    in_tool_call_tag: bool = False
    in_json_tool_call: bool = False
    json_brace_depth: int = 0
    has_streamed_content: bool = False