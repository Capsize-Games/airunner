"""Planning phase mixin for DeepResearchAgent.

Handles research planning, progress updates, and RAG checks.
"""

import os
import logging
from datetime import datetime

from airunner.components.llm.tools.research_document_tools import (
    create_research_document,
)
from airunner.components.llm.tools.rag_tools import (
    search_knowledge_base_documents,
)
from airunner.components.llm.managers.llm_response import LLMResponse
from airunner.enums import SignalCode
from typing import TypedDict

logger = logging.getLogger(__name__)


class DeepResearchState(TypedDict):
    """Type definition for deep research state."""

    messages: list
    current_phase: str
    research_topic: str
    clean_topic: str
    search_queries: list
    document_path: str
    notes_path: str
    scraped_urls: list


class PlanningPhaseMixin:
    """Provides research planning and initialization methods."""

    def _plan_research(self, state: DeepResearchState) -> dict:
        """Generate comprehensive research plan with multiple search queries."""
        messages = state.get("messages", [])
        if not messages:
            return {}

        last_msg = self._get_last_human_message(messages)
        if not last_msg:
            return {}

        user_prompt = str(last_msg.content)
        clean_topic = self._parse_research_prompt(user_prompt)
        logger.info(
            f"[Plan] Parsed topic: '{clean_topic}' from prompt: '{user_prompt}'"
        )

        professional_title = (
            "[WORKING DRAFT] " + self._generate_professional_title(clean_topic)
        )
        logger.info(f"[Plan] Generated working title: {professional_title}")

        document_path = self._create_document_path(professional_title)
        search_queries = self._generate_search_queries(clean_topic)

        logger.info(
            f"Deep research plan: title='{professional_title}', "
            f"clean_topic='{clean_topic}', queries={len(search_queries)}, path={document_path}"
        )

        self._emit_progress(
            "Planning Complete",
            f"Prepared {len(search_queries)} search queries",
        )

        return {
            "research_topic": professional_title,
            "clean_topic": clean_topic,
            "user_prompt": user_prompt,
            "search_queries": search_queries,
            "collected_sources": [],
            "current_phase": "phase0",
            "rag_loaded": False,
            "sources_scraped": 0,
            "scraped_urls": [],
            "sections_written": [],
            "notes_path": "",
            "outline": "",
            "document_path": document_path,
            "thesis_statement": "",
            "previous_sections": {},
        }

    def _get_last_human_message(self, messages: list):
        """Extract last human message from message list."""
        for msg in reversed(messages):
            if hasattr(msg, "type") and msg.type == "human":
                return msg
        return None

    def _create_document_path(self, professional_title: str) -> str:
        """Create research document and return its path."""
        document_path = None
        try:
            document_path = create_research_document(
                topic=professional_title, api=self._api
            )

            # CRITICAL: Validate the returned path is not an error message
            if not document_path:
                logger.error("[Plan] Document creation returned None/empty")
                raise ValueError("Document path is empty")

            if "Error" in document_path or not os.path.exists(document_path):
                logger.error(
                    f"[Plan] Document creation failed or returned invalid path: {document_path}"
                )
                raise ValueError(f"Invalid document path: {document_path}")

            logger.info(f"[Plan] Created research document: {document_path}")
            return document_path
        except Exception as e:
            logger.error(
                f"[Plan] Failed to create research document: {e}",
                exc_info=True,
            )
            # Create fallback path
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_topic = "".join(
                c if c.isalnum() or c in (" ", "_") else "_"
                for c in professional_title[:50]
            )
            safe_topic = "_".join(safe_topic.split())
            filename = f"{timestamp}_{safe_topic}.md"

            # Use the agent's research path
            if hasattr(self, "_research_path"):
                # Ensure the research path directory exists
                os.makedirs(self._research_path, exist_ok=True)
                document_path = str(self._research_path / filename)
            else:
                # Ultimate fallback
                import tempfile

                temp_dir = tempfile.gettempdir()
                fallback_dir = os.path.join(temp_dir, "airunner_research")
                os.makedirs(fallback_dir, exist_ok=True)
                document_path = os.path.join(fallback_dir, filename)

            logger.warning(f"[Plan] Using fallback path: {document_path}")

            # Create empty document at fallback path
            try:
                # Ensure parent directory exists (shouldn't be needed but belt and suspenders)
                parent_dir = os.path.dirname(document_path)
                if parent_dir:
                    os.makedirs(parent_dir, exist_ok=True)

                with open(document_path, "w", encoding="utf-8") as f:
                    f.write(f"# {professional_title}\n\n**Status:** Draft\n\n")
                logger.info(
                    f"[Plan] Created fallback document: {document_path}"
                )
            except Exception as create_error:
                logger.error(
                    f"[Plan] Failed to create fallback document: {create_error}"
                )

            return document_path

    def _generate_search_queries(self, clean_topic: str) -> list:
        """Generate diverse search queries for the research topic."""
        return [
            clean_topic,
            f"{clean_topic} overview background",
            f"{clean_topic} recent news developments",
            f"{clean_topic} analysis expert opinion",
        ]

    def _emit_progress(self, phase: str, message: str):
        """Emit progress update signal to UI."""
        if self._api and hasattr(self._api, "emit_signal"):
            try:
                response = LLMResponse(
                    message=f"**📍 {phase}:** {message}",
                    is_first_message=False,
                    is_end_of_message=True,
                    action=None,
                    request_id=None,
                )
                self._api.emit_signal(
                    SignalCode.LLM_TEXT_STREAMED_SIGNAL, {"response": response}
                )
            except Exception as e:
                logger.warning(f"Failed to emit progress: {e}")

        self._emit_phase_status_tool_update(phase, message)

    def _emit_phase_status_tool_update(self, phase: str, message: str) -> None:
        """Mirror phase progress into the tool status indicator when available."""

        api = getattr(self, "_api", None)
        tool_id = getattr(self, "_tool_status_id", None)
        tool_prompt = getattr(self, "_tool_status_prompt", "")
        if not api or not tool_id or not tool_prompt:
            return

        emitter = getattr(api, "_emit_deep_research_tool_status", None)
        if not callable(emitter):
            return

        detail_text = f"{phase}: {message}".strip()
        try:
            emitter(tool_id, tool_prompt, "starting", details=detail_text)
        except Exception as exc:
            logger.debug(
                f"Failed to emit tool status update for {phase}: {exc}"
            )

    def _phase0_rag_check(self, state: DeepResearchState) -> dict:
        """Phase 0: Check for relevant RAG documents in knowledge base."""
        topic = state.get("research_topic", "")
        logger.info(f"[Phase 0] Checking for relevant RAG documents")

        rag_loaded = False
        try:
            result = search_knowledge_base_documents(query=topic, k=5)
            rag_loaded = bool(result and "No documents found" not in result)
            if rag_loaded:
                logger.info(
                    f"[Phase 0] Found relevant docs: {result[:200]}..."
                )
            else:
                logger.info(f"[Phase 0] No relevant indexed documents found")
        except Exception as e:
            logger.warning(f"[Phase 0] RAG check failed: {e}")

        self._emit_progress("Phase 0", "RAG check complete")

        return {
            "messages": state.get("messages", []),
            "rag_loaded": rag_loaded,
            "current_phase": "phase1a",
        }
