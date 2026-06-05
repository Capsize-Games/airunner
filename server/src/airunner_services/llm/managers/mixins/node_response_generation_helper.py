"""Response-generation helpers for node functions."""

from __future__ import annotations

from typing import Dict, List, Optional

from langchain_core.messages import AIMessage, BaseMessage

from airunner_services.llm.stream_text import combine_stream_chunks
from airunner_services.llm.thinking_parser import strip_thinking_tags


class NodeResponseGenerationHelper:
    """Handle model-response assembly for workflow nodes."""

    def __init__(self, owner) -> None:
        """Store the owning workflow manager."""
        self._owner = owner

    def stream_model_response(
        self,
        prompt: List[BaseMessage],
        generation_kwargs: Optional[Dict] = None,
    ) -> AIMessage:
        """Stream one model response while temporarily disabling tools."""
        generation_kwargs = generation_kwargs or {}
        chat_model = self._owner._chat_model
        tools_backup = getattr(chat_model, "tools", None)
        tool_choice_backup = getattr(chat_model, "tool_choice", None)
        mode_backup = getattr(chat_model, "tool_calling_mode", None)
        json_mode_backup = getattr(chat_model, "use_json_mode", None)
        try:
            if hasattr(chat_model, "tools"):
                chat_model.tools = None
            if hasattr(chat_model, "tool_choice"):
                chat_model.tool_choice = None
            try:
                if hasattr(chat_model, "tool_calling_mode"):
                    chat_model.tool_calling_mode = "react"
            except AttributeError:
                pass
            if hasattr(chat_model, "use_json_mode"):
                chat_model.use_json_mode = False
            return self._owner._get_streaming_response_helper().generate_streaming_response(
                prompt,
                generation_kwargs,
            )
        finally:
            if hasattr(chat_model, "tools"):
                chat_model.tools = tools_backup
            if hasattr(chat_model, "tool_choice"):
                chat_model.tool_choice = tool_choice_backup
            try:
                if hasattr(chat_model, "tool_calling_mode"):
                    chat_model.tool_calling_mode = mode_backup
            except AttributeError:
                pass
            if hasattr(chat_model, "use_json_mode"):
                chat_model.use_json_mode = json_mode_backup

    def generate_fallback_response(self, tool_name: str) -> str:
        """Generate one fallback response for insufficient tool results."""
        if tool_name == "search_web":
            response_content = (
                "I searched the internet but couldn't find relevant "
                "information on that topic. Could you try rephrasing your "
                "question or asking about something else?"
            )
        elif tool_name == "rag_search":
            response_content = (
                "I searched through the available documents but couldn't "
                "find information about that. The documents may not contain "
                "details on this topic."
            )
        else:
            response_content = (
                "I tried to find information but wasn't able to get useful "
                "results. Could you rephrase your question or try a "
                "different approach?"
            )
        if self._owner._token_callback:
            self._owner._token_callback(response_content)
        return response_content

    def generate_response(
        self, formatted_prompt, generation_kwargs: Dict
    ) -> Optional[AIMessage]:
        """Generate one response using streaming when available."""
        if hasattr(self._owner._chat_model, "stream"):
            return self._owner._get_streaming_response_helper().generate_streaming_response(
                formatted_prompt,
                generation_kwargs,
            )
        return self.generate_invoke_response(formatted_prompt)

    def is_tool_call_json(self, text: str) -> bool:
        """Return whether one text chunk looks like tool-call JSON."""
        stripped = text.strip()
        if not stripped.startswith("{"):
            return False
        if ('"name"' in stripped or '"tool"' in stripped) and (
            '"arguments"' in stripped or '"args"' in stripped
        ):
            return True
        if '"function"' in stripped and '"arguments"' in stripped:
            return True
        return False

    def create_streamed_message(
        self,
        streamed_content: List[str],
        last_chunk_message: Optional[BaseMessage],
        collected_tool_calls: Optional[List] = None,
        thinking_content: Optional[str] = None,
    ) -> AIMessage:
        """Create one AIMessage from streamed content and tool calls."""
        additional_kwargs = {}
        tool_calls = collected_tool_calls or []
        if last_chunk_message is not None:
            additional_kwargs = getattr(
                last_chunk_message, "additional_kwargs", {}
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
        return AIMessage(
            content=complete_content,
            additional_kwargs=additional_kwargs,
            tool_calls=tool_calls or [],
        )

    def generate_invoke_response(self, formatted_prompt) -> AIMessage:
        """Generate one non-streaming response and strip thinking tags."""
        response_message = self._owner._chat_model.invoke(formatted_prompt)
        if hasattr(response_message, "content") and response_message.content:
            cleaned_content = strip_thinking_tags(response_message.content)
            if cleaned_content != response_message.content:
                return AIMessage(
                    content=cleaned_content,
                    additional_kwargs=getattr(
                        response_message,
                        "additional_kwargs",
                        {},
                    ),
                    tool_calls=getattr(response_message, "tool_calls", [])
                    or [],
                )
        return response_message
