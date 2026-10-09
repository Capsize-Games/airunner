"""Shared LLM response payload (issue Capsize-Games/airunner#2188).

Desktop (``airunner``) and services (``airunner-services``) each carried
their own ``LLMResponse`` dataclass. Desktop's genuinely crosses the
desktop/daemon wire (NDJSON chunks over HTTP, reconstructed on the
receiving side field-by-field); services' own copy never leaves its
process. Every consumer on both sides reads fields defensively
(``getattr``/``None``-checked, never ``hasattr``-branching on presence),
so the two shapes are safe to union into one definition here: fields one
side never populates simply stay at their default for that side.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from airunner_common.contract_enums import LLMActionType


@dataclass
class LLMResponse:
    """Represent one streamed or complete LLM response payload."""

    message: str = ""
    is_first_message: bool = False
    is_end_of_message: bool = False
    name: Optional[str] = None
    action: LLMActionType = LLMActionType.CHAT
    node_id: Optional[str] = None
    sequence_number: int = 0
    request_id: Optional[str] = None
    tools: Optional[List[str]] = None
    is_system_message: bool = False
    message_type: Optional[str] = None
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    total_tokens: Optional[int] = None

    # Desktop GUI fields: reasoning-display and tool-status widgets.
    thinking_content: Optional[str] = None
    tool_name: Optional[str] = None
    tool_arguments: Optional[Dict[str, Any]] = None
    tool_status: Optional[str] = None

    # Services fields: headless TTS buffering, Ollama/OpenAI-compat
    # surfaces, and multi-turn orchestration.
    final_visible_message: Optional[str] = None
    skip_tts_stream: bool = False
    tool_calls: Optional[list] = None
    turn_index: int = 0
