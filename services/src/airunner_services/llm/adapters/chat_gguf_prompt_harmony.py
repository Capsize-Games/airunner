"""Harmony prompt-rendering helpers for the GGUF chat adapter."""

from airunner_services.llm.adapters.chat_gguf_prompt_harmony_completion import (
    build_gpt_oss_completion_kwargs,
    continue_prefilled_gpt_oss_tool_call,
    prefilled_gpt_oss_tool_json_needs_continuation,
    render_gpt_oss_harmony_prompt,
)
from airunner_services.llm.adapters.chat_gguf_prompt_harmony_render import (
    render_gpt_oss_ai_message,
    render_gpt_oss_developer_message,
    render_gpt_oss_prefilled_tool_call,
    render_gpt_oss_tool_message,
    render_harmony_message,
    stringify_harmony_content,
)
