"""Response decoding and tool-call helpers for generation mixins."""

from __future__ import annotations

from typing import Any


def decode_response(adapter: Any, outputs: Any, inputs: dict[str, Any]) -> str:
    """Decode one generated response from model outputs."""
    input_length = inputs["input_ids"].shape[1]
    generated_tokens = outputs[0][input_length:]
    if adapter.use_mistral_native and adapter._mistral_tokenizer:
        return _decode_mistral_response(adapter, generated_tokens)
    if adapter.tokenizer:
        return adapter.tokenizer.decode(
            generated_tokens,
            skip_special_tokens=True,
        )
    raise ValueError(
        "No tokenizer available for decoding. Ensure mistral_common is "
        "initialized for the current model."
    )


def _decode_mistral_response(adapter: Any, generated_tokens: Any) -> str:
    """Decode one Mistral-native response payload."""
    response_text = (
        adapter._mistral_tokenizer.instruct_tokenizer.tokenizer.decode(
            generated_tokens.tolist()
        )
    )
    adapter.logger.debug(
        "Mistral decoded response length: %s",
        len(response_text),
    )
    return response_text


def parse_tool_calls_if_enabled(
    adapter: Any,
    response_text: str,
    kwargs: dict[str, Any],
) -> tuple[Any, str]:
    """Parse tool calls when tools are enabled for this response."""
    if not adapter.tools or kwargs.get("disable_tool_parsing", False):
        return None, response_text
    tool_parser, mode_name = _tool_call_parser(adapter)
    tool_calls, cleaned_text = tool_parser(response_text)
    return _log_tool_parse(adapter, tool_calls, cleaned_text, mode_name)


def _tool_call_parser(adapter: Any) -> tuple[Any, str]:
    """Return the active tool-call parser and its logging label."""
    if adapter.tool_calling_mode == "native" and adapter.use_mistral_native:
        return adapter._parse_mistral_tool_calls, "Mistral native"
    if adapter.tool_calling_mode == "json" and adapter.use_json_mode:
        return adapter._parse_json_mode_tool_calls, "JSON mode"
    return adapter._parse_tool_calls, "ReAct"


def _log_tool_parse(
    adapter: Any,
    tool_calls: Any,
    cleaned_text: str,
    mode_name: str,
) -> tuple[Any, str]:
    """Log one tool-call parse result when tool calls were found."""
    if tool_calls:
        adapter.logger.debug(
            "%s extracted %s tool call(s)",
            mode_name,
            len(tool_calls),
        )
    return tool_calls, cleaned_text
