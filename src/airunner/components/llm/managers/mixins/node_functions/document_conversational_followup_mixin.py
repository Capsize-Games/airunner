"""Document conversational follow-up helpers for node functions."""

from typing import Dict, List, Optional, Tuple

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage


class DocumentConversationalFollowupMixin:
    """Run the final conversational pass for grounded document answers."""

    def _build_document_conversational_followup_instruction(
        self,
        grounded_answer: str,
        *,
        user_question: str,
    ) -> str:
        """Return one standard-chat follow-up instruction for document replies."""
        return (
            "Use the grounded document answer below as the factual basis for "
            "your final reply. Answer conversationally and naturally, staying "
            "consistent with the ongoing conversation and system prompt. Do "
            "not mention internal stages, verification, tools, search results, "
            "or evidence labels. Do not add unsupported facts. Preserve any "
            "important uncertainty that already appears in the grounded answer.\n\n"
            f"User question:\n{user_question}\n\n"
            f"Grounded document answer:\n{grounded_answer}"
        )

    def _build_document_conversational_messages(
        self,
        message_history: Optional[List[BaseMessage]],
        *,
        user_question: str,
        grounded_answer: str,
    ) -> List[BaseMessage]:
        """Return history plus one final conversationalization instruction."""
        history: List[BaseMessage] = []
        history.extend(message_history or [])
        if not history and user_question:
            history = [HumanMessage(content=user_question)]
        instruction = self._build_document_conversational_followup_instruction(
            grounded_answer,
            user_question=user_question,
        )
        history.append(HumanMessage(content=instruction))
        return history

    @staticmethod
    def _document_stage_thinking_block(
        stage_title: str,
        response_message: Optional[AIMessage],
    ) -> str:
        """Return one persisted thinking block for a document-answer stage."""
        if response_message is None:
            return ""
        additional_kwargs = (
            getattr(response_message, "additional_kwargs", {}) or {}
        )
        thinking_content = (
            additional_kwargs.get("thinking_content")
            or additional_kwargs.get("reasoning_content")
            or ""
        )
        thinking_text = str(thinking_content).strip()
        if not thinking_text:
            return ""
        return f"{stage_title}\n\n{thinking_text}"

    def _merge_document_stage_thinking(
        self,
        final_message: AIMessage,
        stage_messages: Optional[List[Tuple[str, Optional[AIMessage]]]] = None,
    ) -> AIMessage:
        """Persist thinking from internal document stages with the final reply."""
        additional_kwargs = dict(
            getattr(final_message, "additional_kwargs", {}) or {}
        )
        thinking_sections = []
        for stage_title, stage_message in stage_messages or []:
            block = self._document_stage_thinking_block(
                stage_title,
                stage_message,
            )
            if block:
                thinking_sections.append(block)
        final_block = self._document_stage_thinking_block(
            "Final Conversational Reply",
            final_message,
        )
        if final_block:
            thinking_sections.append(final_block)
        if thinking_sections:
            additional_kwargs["thinking_content"] = "\n\n".join(
                thinking_sections
            )
        return AIMessage(
            content=final_message.content,
            additional_kwargs=additional_kwargs,
            tool_calls=[],
        )

    def _run_document_conversational_pass(
        self,
        grounded_answer: str,
        *,
        user_question: str,
        message_history: Optional[List[BaseMessage]],
        generation_kwargs: Optional[Dict] = None,
        stage_messages: Optional[List[Tuple[str, Optional[AIMessage]]]] = None,
        reject_structure_only: bool = False,
    ) -> Optional[AIMessage]:
        """Run one final normal-chat pass over a grounded document answer."""
        if not str(grounded_answer or "").strip():
            return None
        followup_messages = self._build_document_conversational_messages(
            message_history,
            user_question=user_question,
            grounded_answer=grounded_answer,
        )
        prompt = self._build_prompt(followup_messages)
        response_message = self._stream_model_response(
            prompt,
            generation_kwargs or {},
        )
        visible_content = self._recover_forced_response_content(
            response_message,
            reject_structure_only=reject_structure_only,
        )
        if self._looks_like_instruction_reflection(visible_content):
            visible_content = ""
        if not visible_content:
            return None
        merged_message = AIMessage(
            content=visible_content,
            additional_kwargs=getattr(response_message, "additional_kwargs", {}),
            tool_calls=[],
        )
        return self._merge_document_stage_thinking(
            merged_message,
            stage_messages=stage_messages,
        )