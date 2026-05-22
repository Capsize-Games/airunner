"""Document response policy helpers for node functions."""

import re
from typing import List, Optional

from langchain_core.messages import AIMessage, BaseMessage


class DocumentResponsePolicyMixin:
    """Provide deterministic document-response and routing decisions."""

    def _should_verify_document_response(
        self,
        tool_name: str,
        user_question: str,
    ) -> bool:
        """Return whether a synthesized document answer needs verification."""
        if not self._is_document_result_tool(tool_name):
            return False
        return self._get_document_query_intent(user_question) not in {
            "identity",
            "structure",
        }

    def _should_accept_verified_document_response(
        self,
        verified_message: Optional[AIMessage],
        *,
        reject_structure_only: bool,
    ) -> bool:
        """Return whether the verifier produced one user-facing answer."""
        if verified_message is None:
            return False
        if (
            reject_structure_only
            or self._get_document_answer_mode() == "synthesized"
        ):
            verified_content = self._extract_committed_response_content(
                verified_message,
                reject_structure_only=reject_structure_only,
            )
            return bool(verified_content.strip())
        verified_content = self._recover_forced_response_content(
            verified_message,
            reject_structure_only=reject_structure_only,
        )
        return bool(verified_content.strip())

    def _should_run_document_conversational_pass(
        self,
        tool_name: str,
    ) -> bool:
        """Return whether one document reply should run a final chat pass."""
        if not self._is_document_result_tool(tool_name):
            return False
        return self._get_document_answer_mode() != "synthesized"

    def _build_deterministic_document_response(
        self,
        all_tool_content: str,
        tool_name: str,
        user_question: str,
    ) -> str:
        """Return one direct document answer when synthesis is unnecessary."""
        if not self._is_document_result_tool(tool_name):
            return ""

        if self._get_document_answer_mode() not in (None, "deterministic"):
            return ""

        document_intent = self._get_document_query_intent(user_question)
        if document_intent == "identity":
            return self._build_document_identity_response(all_tool_content)
        if document_intent == "structure":
            return self._build_document_structure_response(all_tool_content)
        return ""

    @staticmethod
    def _is_document_result_tool(tool_name: str) -> bool:
        """Return whether one tool is part of the document QA pipeline."""
        return tool_name in {
            "inspect_loaded_documents",
            "rag_search",
            "analyze_loaded_document",
        }

    def _should_force_document_tool_response(self, tool_name: str) -> bool:
        """Return whether one document tool should bypass replanning."""
        llm_request = getattr(self, "llm_request", None)
        request_plan = getattr(llm_request, "request_plan", None)
        if getattr(llm_request, "planner_mode", None) == "select_tools":
            return False
        if tool_name == "inspect_loaded_documents":
            return True
        if self._get_document_answer_mode() == "synthesized":
            return False
        primary_tool = getattr(request_plan, "primary_tool", None)
        if not primary_tool:
            primary_tool = getattr(llm_request, "document_primary_tool", None)
        if not primary_tool:
            primary_tool = getattr(llm_request, "preprocessed_primary_tool", None)
        if isinstance(primary_tool, str) and primary_tool:
            return tool_name == primary_tool
        return False

    def _should_disable_tools_for_followup(
        self,
        messages: List[BaseMessage],
    ) -> bool:
        """Return whether the next model turn should answer without tools."""
        if self._get_document_answer_mode() != "synthesized":
            return False
        current_turn_messages = self._get_current_turn_messages(messages)
        last_ai_msg = self._get_last_tool_calling_ai_message(
            current_turn_messages
        )
        if not last_ai_msg or not getattr(last_ai_msg, "tool_calls", None):
            return False
        return any(
            self._is_document_result_tool(str(tool_call.get("name") or ""))
            for tool_call in last_ai_msg.tool_calls
        )

    def _should_use_grounded_document_followup(
        self,
        messages: List[BaseMessage],
    ) -> bool:
        """Return whether synthesized follow-up should use grounded reply flow."""
        if self._get_document_answer_mode() != "synthesized":
            return False

        current_turn_messages = self._get_current_turn_messages(messages)
        last_ai_msg = self._get_last_tool_calling_ai_message(
            current_turn_messages
        )
        if not last_ai_msg or not getattr(last_ai_msg, "tool_calls", None):
            return False

        return any(
            str(tool_call.get("name") or "") == "analyze_loaded_document"
            for tool_call in last_ai_msg.tool_calls
        )

    def _get_document_query_intent(self, user_question: str) -> str | None:
        """Return the request-scoped document intent when available."""
        llm_request = getattr(self, "llm_request", None)
        request_plan = getattr(llm_request, "request_plan", None)
        intent = getattr(request_plan, "document_query_intent", None)
        if isinstance(intent, str) and intent:
            return intent
        intent = getattr(llm_request, "document_query_intent", None)
        if isinstance(intent, str) and intent:
            return intent
        return None

    def _get_document_answer_mode(self) -> str | None:
        """Return the request-scoped document answer mode when available."""
        llm_request = getattr(self, "llm_request", None)
        request_plan = getattr(llm_request, "request_plan", None)
        mode = getattr(request_plan, "document_answer_mode", None)
        if isinstance(mode, str) and mode:
            return mode
        mode = getattr(llm_request, "document_answer_mode", None)
        if isinstance(mode, str) and mode:
            return mode
        return None

    def _get_document_summary_focus(
        self,
        user_question: str,
    ) -> str | None:
        """Return the request-scoped summary subtype when available."""
        llm_request = getattr(self, "llm_request", None)
        request_plan = getattr(llm_request, "request_plan", None)
        focus = getattr(request_plan, "document_summary_focus", None)
        if isinstance(focus, str) and focus:
            return focus
        focus = getattr(llm_request, "document_summary_focus", None)
        if isinstance(focus, str) and focus:
            return focus
        return None

    @staticmethod
    def _build_document_identity_response(all_tool_content: str) -> str:
        """Return one direct document identity answer from tool results."""
        label = title = author = file_type = stored_path = ""
        for line in all_tool_content.splitlines():
            stripped = line.strip()
            if stripped.startswith("Document 1: ") and not label:
                label = stripped.removeprefix("Document 1: ").strip()
            elif stripped.startswith("Inferred title from filename: "):
                title = stripped.removeprefix(
                    "Inferred title from filename: "
                ).strip()
            elif stripped.startswith("Inferred author from filename: "):
                author = stripped.removeprefix(
                    "Inferred author from filename: "
                ).strip()
            elif stripped.startswith("File type: "):
                file_type = stripped.removeprefix("File type: ").strip()
            elif stripped.startswith("Stored path: "):
                stored_path = stripped.removeprefix("Stored path: ").strip()

        type_label = file_type.lstrip(".").upper()
        if title and author:
            descriptor = (
                f"a {type_label} document" if type_label else "a document"
            )
            return f"This document is {descriptor} titled '{title}' by {author}."
        if title:
            descriptor = (
                f"a {type_label} document" if type_label else "a document"
            )
            return f"This document is {descriptor} titled '{title}'."
        if label:
            descriptor = f"the {type_label} file" if type_label else "the file"
            return f"This document is {descriptor} '{label}'."
        if stored_path:
            return f"This document is stored at '{stored_path}'."
        return ""

    @staticmethod
    def _build_document_structure_response(all_tool_content: str) -> str:
        """Return one direct structure answer from tool results."""
        headings: list[str] = []
        capture_structure = False

        for line in str(all_tool_content or "").splitlines():
            stripped = line.strip()
            if stripped == "Document structure:":
                capture_structure = True
                continue
            if not capture_structure or not stripped:
                continue
            if stripped.startswith("--- Tool Result"):
                break

            match = re.match(r"^\d+\.\s+(.+)$", stripped)
            if not match:
                if headings:
                    break
                continue

            headings.append(match.group(1).strip())

        return "\n".join(headings)