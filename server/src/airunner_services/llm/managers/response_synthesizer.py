"""Forced-response synthesis helpers for workflow nodes."""

from __future__ import annotations

from typing import Any, Dict, Optional

from langchain_core.messages import AIMessage, HumanMessage

from airunner_services.llm.managers.workflow_response_prompts import (
    build_tool_result_response_prompt,
)


class ResponseSynthesizer:
    """Generate post-tool responses while preserving streaming semantics."""

    MESSAGE_FALLBACK = (
        "I found some information but encountered an issue generating a "
        "complete response."
    )
    TEXT_FALLBACK = (
        "I found some information but encountered an issue generating a "
        "complete response. Let me try to help with what I found."
    )

    def __init__(self, owner: Any):
        self._owner = owner

    def generate_forced_response_message(
        self,
        tool_content: str,
        tool_name: str,
        user_question: str,
        generation_kwargs: Optional[Dict] = None,
    ) -> AIMessage:
        """Return a final AI message from tool results."""
        try:
            response_message = self.generate_response_message_from_results(
                tool_content,
                tool_name,
                user_question,
                generation_kwargs,
            )
            if response_message is not None:
                return response_message
        except Exception as exc:
            self._owner.logger.error(
                "Failed to generate forced response: %s",
                exc,
            )

        self._stream_fallback(self.MESSAGE_FALLBACK)
        return AIMessage(content=self.MESSAGE_FALLBACK, tool_calls=[])

    def generate_forced_response_text(
        self,
        tool_content: str,
        tool_name: str,
        user_question: str,
        generation_kwargs: Optional[Dict] = None,
    ) -> str:
        """Return plain response text synthesized from tool results."""
        try:
            return self.generate_response_text_from_results(
                tool_content,
                tool_name,
                user_question,
                generation_kwargs,
            )
        except Exception as exc:
            self._owner.logger.error(
                "Failed to generate forced response: %s",
                exc,
            )

        self._stream_fallback(self.TEXT_FALLBACK)
        return self.TEXT_FALLBACK

    def generate_response_message_from_results(
        self,
        all_tool_content: str,
        tool_name: str,
        user_question: str = "",
        generation_kwargs: Optional[Dict] = None,
    ) -> Optional[AIMessage]:
        """Return an AI message and preserve thinking metadata."""
        self._owner.logger.info(
            "Forcing model to answer based on %s results "
            "(preserving thinking)...",
            tool_name,
        )
        response_message = self._stream_response_message(
            all_tool_content,
            user_question,
            generation_kwargs,
        )
        if response_message is None:
            return None

        return AIMessage(
            content=response_message.content or "",
            additional_kwargs=getattr(
                response_message,
                "additional_kwargs",
                {},
            ),
            tool_calls=[],
        )

    def generate_response_text_from_results(
        self,
        all_tool_content: str,
        tool_name: str,
        user_question: str = "",
        generation_kwargs: Optional[Dict] = None,
    ) -> str:
        """Return plain response text from streamed tool-result synthesis."""
        self._owner.logger.info(
            "Forcing model to answer based on %s results...",
            tool_name,
        )
        response_message = self._stream_response_message(
            all_tool_content,
            user_question,
            generation_kwargs,
        )
        response_content = ""
        if response_message is not None and hasattr(
            response_message, "content"
        ):
            response_content = response_message.content or ""

        self._owner.logger.info(
            "Model streamed %s char answer",
            len(response_content),
        )
        return response_content

    def _stream_response_message(
        self,
        all_tool_content: str,
        user_question: str,
        generation_kwargs: Optional[Dict] = None,
    ) -> Any:
        """Stream one synthesized response from tool results."""
        prompt = [
            HumanMessage(
                content=build_tool_result_response_prompt(
                    all_tool_content=all_tool_content,
                    user_question=user_question,
                )
            )
        ]
        return self._owner._stream_model_response(prompt, generation_kwargs)

    def _stream_fallback(self, fallback: str) -> None:
        """Emit fallback text through the token callback when available."""
        if self._owner._token_callback:
            self._owner._token_callback(fallback)
