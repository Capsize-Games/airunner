"""Response generation helpers for node functions."""

from typing import Any, Dict, List, Optional

from langchain_core.messages import AIMessage, BaseMessage

from airunner.components.llm.utils.stream_text import combine_stream_chunks
from airunner.components.llm.utils.thinking_parser import (
    strip_thinking_tags,
)


class ResponseGenerationMixin:
    """Generate model responses and normalize message payloads."""

    def _generate_response(
        self,
        formatted_prompt: Any,
        generation_kwargs: Dict[str, Any],
    ) -> Optional[AIMessage]:
        """Generate a response via the streaming or invoke path."""
        chat_model = getattr(self, "_chat_model", None)
        if chat_model is None:
            self.logger.error(
                "[CALL MODEL DEBUG] No chat model configured for response "
                "generation"
            )
            return None

        if hasattr(chat_model, "stream"):
            return self._generate_streaming_response(
                formatted_prompt,
                generation_kwargs,
            )

        return self._generate_invoke_response(formatted_prompt)

    def _build_request_tool_debug_metadata(
        self,
    ) -> Optional[Dict[str, Any]]:
        """Return a request-settings snapshot for tool rows."""
        llm_request = getattr(self, "llm_request", None)
        if llm_request is None:
            return None

        build_metadata = getattr(llm_request, "to_debug_metadata", None)
        if not callable(build_metadata):
            return None

        metadata = build_metadata(title="Request Settings")
        return metadata if isinstance(metadata, dict) else None

    def _create_streamed_message(
        self,
        streamed_content: List[str],
        last_chunk_message: Optional[BaseMessage],
        collected_tool_calls: Optional[List] = None,
        thinking_content: Optional[str] = None,
        thinking_metadata: Optional[Dict[str, Any]] = None,
    ) -> AIMessage:
        """Create an AI message from streamed content."""
        additional_kwargs = {}
        tool_calls = collected_tool_calls or []

        if last_chunk_message is not None:
            additional_kwargs = getattr(
                last_chunk_message,
                "additional_kwargs",
                {},
            )
            if not collected_tool_calls:
                tool_calls = (
                    getattr(last_chunk_message, "tool_calls", None) or []
                )

        visible_chunks = []
        for chunk in streamed_content:
            cleaned_chunk = strip_thinking_tags(chunk)
            if cleaned_chunk:
                visible_chunks.append(cleaned_chunk)

        complete_content = combine_stream_chunks(visible_chunks)

        if thinking_content:
            additional_kwargs = dict(additional_kwargs)
            additional_kwargs["thinking_content"] = thinking_content
        if thinking_metadata:
            additional_kwargs = dict(additional_kwargs)
            additional_kwargs["thinking_metadata"] = thinking_metadata

        if tool_calls and "tool_status_metadata" not in additional_kwargs:
            tool_status_metadata = self._build_request_tool_debug_metadata()
            if tool_status_metadata:
                additional_kwargs = dict(additional_kwargs)
                additional_kwargs["tool_status_metadata"] = (
                    tool_status_metadata
                )

        return AIMessage(
            content=complete_content,
            additional_kwargs=additional_kwargs,
            tool_calls=tool_calls or [],
        )

    def _generate_invoke_response(self, formatted_prompt: Any) -> AIMessage:
        """Generate a response through the non-streaming invoke path."""
        response_message = self._chat_model.invoke(formatted_prompt)

        if hasattr(response_message, "content") and response_message.content:
            cleaned_content = strip_thinking_tags(response_message.content)
            if cleaned_content != response_message.content:
                response_message = AIMessage(
                    content=cleaned_content,
                    additional_kwargs=getattr(
                        response_message,
                        "additional_kwargs",
                        {},
                    ),
                    tool_calls=(
                        getattr(response_message, "tool_calls", []) or []
                    ),
                )

        tool_calls = getattr(response_message, "tool_calls", []) or []
        additional_kwargs = (
            getattr(response_message, "additional_kwargs", {}) or {}
        )
        if tool_calls and "tool_status_metadata" not in additional_kwargs:
            tool_status_metadata = self._build_request_tool_debug_metadata()
            if tool_status_metadata:
                additional_kwargs = dict(additional_kwargs)
                additional_kwargs["tool_status_metadata"] = (
                    tool_status_metadata
                )
                response_message = AIMessage(
                    content=getattr(response_message, "content", "") or "",
                    additional_kwargs=additional_kwargs,
                    tool_calls=tool_calls,
                )

        if (
            self._token_callback
            and hasattr(response_message, "content")
            and response_message.content
        ):
            try:
                self._token_callback(response_message.content)
            except Exception as callback_error:
                self.logger.error(
                    "Token callback failed: %s",
                    callback_error,
                    exc_info=True,
                )

        return response_message