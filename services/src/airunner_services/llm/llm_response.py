"""Service-owned response model for streamed LLM output."""

from dataclasses import dataclass
from typing import Optional
from airunner_services.utils.application.enum_resolver import llm_action_type


LLMActionType = llm_action_type()


@dataclass
class LLMResponse:
    """Represent one streamed or complete LLM response payload."""

    message: str = ""
    final_visible_message: Optional[str] = None
    skip_tts_stream: bool = False
    is_first_message: bool = False
    is_end_of_message: bool = False
    name: Optional[str] = None
    action: object = LLMActionType.CHAT
    node_id: Optional[str] = None
    sequence_number: int = 0
    request_id: Optional[str] = None
    tools: Optional[list] = None
    is_system_message: bool = False
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    message_type: Optional[str] = None
    turn_index: int = 0