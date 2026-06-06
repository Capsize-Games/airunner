"""Compatibility exports for generation stream helpers."""

from airunner_services.llm.managers.mixins.generation_signal_support import (
    create_streaming_callback,
    create_thinking_callback,
    emit_visible_response,
    send_end_of_message,
)
from airunner_services.llm.managers.mixins.generation_usage import (
    executed_tools_from_workflow,
    extract_usage_tokens,
)
from airunner_services.llm.managers.mixins.generation_response_support import (
    extract_final_response,
    fallback_response_for_empty_result,
    handle_generation_error,
    handle_interrupted_generation,
)

__all__ = [
    "create_streaming_callback",
    "create_thinking_callback",
    "emit_visible_response",
    "executed_tools_from_workflow",
    "extract_final_response",
    "extract_usage_tokens",
    "fallback_response_for_empty_result",
    "handle_generation_error",
    "handle_interrupted_generation",
    "send_end_of_message",
]
