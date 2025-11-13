"""Review phase mixin for DeepResearchAgent.

Handles Phase 1E and 1F: reviewing document quality, applying corrections, and finalizing.
"""

import re
import logging
from pathlib import Path
from typing import TypedDict

from airunner.components.llm.tools.research_document_tools import (
    finalize_research_document,
)

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


class ReviewPhaseMixin:
    """Provides Phase 1E and 1F review, revision, and finalization methods."""

    def _phase1e_review(self, state: DeepResearchState) -> dict:
        """
        Phase 1E: Review and validate document quality.

        Checks:
        - All sections are present
        - Citations are included
        - Content is substantial
        - No raw notes remain
        - FACTUAL ACCURACY (multiple passes)

        Returns:
            Updated state with review notes
        """
        document_path = state.get("document_path", "")
        thesis = state.get("thesis_statement", "")

        logger.info(
            f"[Phase 1E] Reviewing document for quality AND factual accuracy"
        )
        self._emit_progress("Phase 1E", "Reviewing document quality and facts")

        if not document_path or not Path(document_path).exists():
            logger.error(f"[Phase 1E] Document not found: {document_path}")
            return {
                "messages": state.get("messages", []),
                "current_phase": "phase1f",
            }

        # Read document
        try:
            with open(document_path, "r", encoding="utf-8") as f:
                doc_content = f.read()
        except Exception as e:
            logger.error(f"[Phase 1E] Failed to read document: {e}")
            return {
                "messages": state.get("messages", []),
                "current_phase": "phase1f",
            }

        # Review checks
        review_notes = []

        # Check for required sections
        required_sections = [
            "Introduction",
            "Background",
            "Analysis",
            "Implications",
            "Conclusion",
        ]
        for section in required_sections:
            if f"## {section}" not in doc_content:
                review_notes.append(f"Missing section: {section}")
                logger.warning(f"[Phase 1E] Missing section: {section}")

        # Check for substance
        if len(doc_content) < 1000:
            review_notes.append("Document is too short")
            logger.warning(
                f"[Phase 1E] Document only {len(doc_content)} chars"
            )

        # Check for source references (look for **Source N** format)
        source_count = len(re.findall(r"\*\*Source \d+\*\*", doc_content))
        if source_count < 3:
            review_notes.append(
                f"Only {source_count} sources cited - expected more"
            )
            logger.warning(f"[Phase 1E] Only {source_count} sources found")

        # Check for unprocessed notes markers (shouldn't have ### URLs anymore)
        if re.search(r"###\s+https?://", doc_content):
            review_notes.append("Document may contain unprocessed raw notes")
            logger.warning(f"[Phase 1E] Found potential raw notes markers")

        # CRITICAL: Fact-check the document (multiple passes)
        logger.info(f"[Phase 1E] Running fact-checking pass 1/2")
        self._emit_progress("Phase 1E", "Fact-checking document (pass 1)")
        fact_errors = self._fact_check_document(doc_content, thesis)

        if fact_errors:
            for error in fact_errors:
                review_notes.append(f"FACTUAL ERROR: {error}")
                logger.warning(f"[Phase 1E] Factual error detected: {error}")

        # Second fact-check pass on different sections
        logger.info(f"[Phase 1E] Running fact-checking pass 2/2")
        self._emit_progress("Phase 1E", "Fact-checking document (pass 2)")
        fact_errors_2 = self._fact_check_document(
            doc_content[3000:6000], thesis
        )

        if fact_errors_2:
            for error in fact_errors_2:
                if error not in review_notes:  # Avoid duplicates
                    review_notes.append(f"FACTUAL ERROR: {error}")
                    logger.warning(
                        f"[Phase 1E] Factual error detected (pass 2): {error}"
                    )

        if review_notes:
            logger.info(
                f"[Phase 1E] Review found {len(review_notes)} issues to address"
            )
            for note in review_notes:
                logger.info(f"  - {note}")
        else:
            logger.info(f"[Phase 1E] Document passed all quality checks")

        self._emit_progress(
            "Phase 1E",
            (
                f"Review complete - {len(review_notes)} issues found (including fact-check)"
                if review_notes
                else "Review complete - quality and facts approved"
            ),
        )

        return {
            "messages": state.get("messages", []),
            "review_notes": review_notes,
            "current_phase": "phase1f",
        }

    # ==================================================================
    # PHASE 1F: REVISE
    # ==================================================================

    def _phase1f_revise(self, state: DeepResearchState) -> dict:
        """Phase 1F: Apply final polishing and improvements, including FACTUAL CORRECTIONS.

        Improvements:
        - Fix factual errors identified in review
        - Add transitions between sections
        - Ensure proper formatting
        - Add executive summary if missing
        - Finalize citations

        Returns:
            Updated state
        """
        document_path = state.get("document_path", "")
        review_notes = state.get("review_notes", [])

        logger.info(
            f"[Phase 1F] Applying final revisions and fact corrections"
        )
        self._emit_progress(
            "Phase 1F", "Correcting facts and polishing document"
        )

        if not document_path or not Path(document_path).exists():
            logger.error(f"[Phase 1F] Document not found: {document_path}")
            return {
                "messages": state.get("messages", []),
                "current_phase": "finalize",
            }

        try:
            with open(document_path, "r", encoding="utf-8") as f:
                doc_content = f.read()
        except Exception as e:
            logger.error(f"[Phase 1F] Failed to read document: {e}")
            return {
                "messages": state.get("messages", []),
                "current_phase": "finalize",
            }

        revisions_applied = []

        # Apply all revisions using helper methods
        factual_errors = [
            note for note in review_notes if "FACTUAL ERROR" in note
        ]
        doc_content, revisions = self._apply_factual_corrections(
            doc_content, factual_errors
        )
        revisions_applied.extend(revisions)

        doc_content, revisions = self._generate_abstract(doc_content)
        revisions_applied.extend(revisions)

        doc_content, revisions = self._generate_table_of_contents(doc_content)
        revisions_applied.extend(revisions)

        doc_content, revisions = self._normalize_section_spacing(doc_content)
        revisions_applied.extend(revisions)

        doc_content, revisions = self._add_source_count_to_title(doc_content)
        revisions_applied.extend(revisions)

        # Write revised document
        try:
            with open(document_path, "w", encoding="utf-8") as f:
                f.write(doc_content)
            logger.info(
                f"[Phase 1F] Applied {len(revisions_applied)} revisions"
            )
            for revision in revisions_applied:
                logger.info(f"  - {revision}")
        except Exception as e:
            logger.error(f"[Phase 1F] Failed to write revisions: {e}")

        self._emit_progress(
            "Phase 1F",
            f"Applied {len(revisions_applied)} improvements (including fact corrections)",
        )

        return {
            "messages": state.get("messages", []),
            "revisions_applied": revisions_applied,
            "current_phase": "finalize",
        }

    # ==================================================================
    # FINALIZATION
    # ==================================================================

    def _finalize_document(self, state: DeepResearchState) -> dict:
        """
        Finalize the research document.

        Args:
            state: Current research state

        Returns:
            Updated state
        """
        document_path = state.get("document_path", "")
        error = state.get("error", "")

        # Check if we have an error state (e.g., no sources found)
        if error:
            logger.error(
                f"[Finalize] Cannot finalize - error occurred: {error}"
            )
            self._emit_progress("Finalize", f"Research failed: {error}")

            # Create an error document if one was started
            if document_path and Path(document_path).exists():
                try:
                    with open(document_path, "a", encoding="utf-8") as f:
                        f.write(f"\n\n---\n\n## Error\n\n{error}\n\n")
                        f.write(
                            "**Status:** Failed - No sources could be gathered.\n"
                        )
                except Exception as e:
                    logger.error(
                        f"[Finalize] Failed to write error message: {e}"
                    )

            return {
                "messages": state.get("messages", []),
                "current_phase": "complete",
                "error": error,
            }

        logger.info(f"[Finalize] Finalizing document: {document_path}")

        try:
            result = finalize_research_document(document_path=document_path)
            logger.info(f"[Finalize] {result}")
            self._emit_progress("Finalize", f"Document ready: {document_path}")
        except Exception as e:
            logger.error(f"[Finalize] Failed to finalize: {e}")

        logger.info(f"✓ Research workflow completed for: {document_path}")

        return {
            "messages": state.get("messages", []),
            "current_phase": "complete",
        }
