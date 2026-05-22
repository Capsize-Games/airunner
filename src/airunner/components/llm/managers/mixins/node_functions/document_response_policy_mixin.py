"""Document response policy helpers for node functions."""

import re
from typing import List, Optional

from langchain_core.messages import AIMessage, BaseMessage

from airunner.components.llm.utils.document_query_routing import (
    route_document_query,
)


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
        verified_content = self._recover_forced_response_content(
            verified_message,
            reject_structure_only=reject_structure_only,
        )
        return bool(verified_content.strip())

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
        return tool_name in {"inspect_loaded_documents", "rag_search"}

    def _should_force_document_tool_response(self, tool_name: str) -> bool:
        """Return whether one document tool should bypass replanning."""
        if tool_name == "inspect_loaded_documents":
            return True
        if self._get_document_answer_mode() == "synthesized":
            return False
        llm_request = getattr(self, "llm_request", None)
        primary_tool = getattr(llm_request, "document_primary_tool", None)
        if isinstance(primary_tool, str) and primary_tool:
            return tool_name == primary_tool
        route = getattr(self, "_current_document_query_route", None)
        return tool_name == "rag_search" and route is not None

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

    def _get_document_query_intent(self, user_question: str) -> str | None:
        """Return the request-scoped document intent when available."""
        llm_request = getattr(self, "llm_request", None)
        intent = getattr(llm_request, "document_query_intent", None)
        if isinstance(intent, str) and intent:
            return intent
        route = getattr(self, "_current_document_query_route", None)
        intent = getattr(route, "intent", None)
        if isinstance(intent, str) and intent:
            return intent
        routed = route_document_query(
            user_question,
            assume_document_mode=True,
        )
        if routed is not None:
            return routed.intent
        if self._is_document_about_question(user_question):
            return "summary"
        if self._is_document_structure_question(user_question):
            return "structure"
        if self._is_document_summary_question(user_question):
            return "summary"
        if self._is_document_identity_question(user_question):
            return "identity"
        return None

    def _get_document_answer_mode(self) -> str | None:
        """Return the request-scoped document answer mode when available."""
        llm_request = getattr(self, "llm_request", None)
        mode = getattr(llm_request, "document_answer_mode", None)
        if isinstance(mode, str) and mode:
            return mode
        route = getattr(self, "_current_document_query_route", None)
        mode = getattr(route, "answer_mode", None)
        if isinstance(mode, str) and mode:
            return mode
        return None

    @staticmethod
    def _is_document_identity_question(user_question: str) -> bool:
        """Return whether the user is asking to identify a document."""
        normalized = " ".join(str(user_question or "").lower().split())
        if not normalized:
            return False

        identity_phrases = (
            "what is this document",
            "what document is this",
            "tell me what this document is",
            "what is this file",
            "what file is this",
            "which document is this",
            "which file is this",
            "identify this document",
            "identify the document",
            "identify this file",
        )
        if any(phrase in normalized for phrase in identity_phrases):
            return True

        asks_identity = any(
            phrase in normalized
            for phrase in ("what is this", "which is this", "identify")
        )
        mentions_document = "document" in normalized or "file" in normalized
        return asks_identity and mentions_document

    @staticmethod
    def _is_document_structure_question(user_question: str) -> bool:
        """Return whether the user is asking for document structure."""
        normalized = " ".join(str(user_question or "").lower().split())
        if not normalized:
            return False

        structure_phrases = (
            "table of contents",
            "what chapters are",
            "what are the chapters",
            "chapter titles",
            "what sections are",
            "list the sections",
            "document structure",
        )
        return any(phrase in normalized for phrase in structure_phrases)

    @staticmethod
    def _is_document_summary_question(user_question: str) -> bool:
        """Return whether the user is asking for a document summary."""
        normalized = " ".join(str(user_question or "").lower().split())
        if not normalized:
            return False

        summary_phrases = (
            "summarize this document",
            "summarize the document",
            "summary of this document",
            "summary of the document",
            "give me a summary",
            "summarize it",
        )
        return any(phrase in normalized for phrase in summary_phrases)

    @staticmethod
    def _is_document_about_question(user_question: str) -> bool:
        """Return whether the user is asking what a document/book is about."""
        normalized = " ".join(str(user_question or "").lower().split())
        if not normalized:
            return False

        patterns = (
            r"\bwhat(?:'s| is)\s+(?:this|the)\s+(?:book|novel|story|document|file)\s+about\b",
            r"\bwhat\s+is\s+the\s+(?:book|novel|story|document|file)\s+about\b",
            r"\btell\s+me\s+about\s+(?:this|the)\s+(?:book|novel|story|document|file)\b",
        )
        return any(re.search(pattern, normalized) for pattern in patterns)

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