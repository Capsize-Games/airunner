"""Prompt and message helpers for the GGUF chat adapter."""

from airunner_services.llm.adapters.chat_gguf_prompt_harmony import (
    build_gpt_oss_completion_kwargs,
    continue_prefilled_gpt_oss_tool_call,
    prefilled_gpt_oss_tool_json_needs_continuation,
    render_gpt_oss_ai_message,
    render_gpt_oss_developer_message,
    render_gpt_oss_harmony_prompt,
    render_gpt_oss_prefilled_tool_call,
    render_gpt_oss_tool_message,
    render_harmony_message,
    stringify_harmony_content,
)
from airunner_services.llm.adapters.chat_gguf_prompt_instructions import (
    apply_gpt_oss_reasoning_effort,
    apply_thinking_directive,
    format_react_tool,
    gpt_oss_harmony_system_message,
    inject_gpt_oss_tool_instructions,
    inject_react_tool_instructions,
    inject_tool_instructions,
)
from airunner_services.llm.adapters.chat_gguf_prompt_messages import (
    convert_messages,
)
from airunner_services.llm.adapters.chat_gguf_tool_call_conversion import (
    convert_langchain_tool_call,
    convert_langchain_tool_calls,
)
from airunner_services.llm.adapters.chat_gguf_prompt_schema import (
    format_gpt_oss_namespace,
    format_gpt_oss_object_type,
    format_gpt_oss_shared_definitions,
    format_gpt_oss_tool,
    format_gpt_oss_type,
)
