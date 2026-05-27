"""Tool-parsing helpers extracted from the ChatGGUF adapter."""

from airunner_services.llm.adapters.chat_gguf_tool_parsing_common import (
    normalize_tool_payload,
    normalize_tool_value,
)
from airunner_services.llm.adapters.chat_gguf_tool_parsing_gpt_oss import (
    build_gpt_oss_message_from_raw,
    extract_gpt_oss_recipient,
    extract_prefilled_gpt_oss_tool_json,
    forced_gpt_oss_tool_name,
    parse_gpt_oss_commentary_tool_calls,
    parse_prefilled_gpt_oss_tool_call,
)
from airunner_services.llm.adapters.chat_gguf_tool_parsing_react import (
    parse_react_tool_calls,
)
