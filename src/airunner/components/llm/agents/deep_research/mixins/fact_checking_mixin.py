"""Fact-checking mixin for DeepResearchAgent.

Provides fact-checking and correction capabilities for research documents.
"""

import re
import logging
from typing import List

from langchain_core.messages import HumanMessage

logger = logging.getLogger(__name__)


class FactCheckingMixin:
    """Provides fact-checking and correction methods."""

    def _fact_check_document(
        self, document_content: str, thesis: str
    ) -> List[str]:
        """
        Use LLM to fact-check the document for accuracy and truthfulness.

        Args:
            document_content: The full document text
            thesis: The thesis statement

        Returns:
            List of factual errors or concerns found
        """
        # Extract key factual claims for review
        prompt = f"""You are a fact-checking expert reviewing a research paper. Carefully examine the following document for FACTUAL ERRORS, especially:

1. Incorrect dates or timelines
2. Wrong job titles or positions (e.g., calling current officials "former")
3. Misattributed quotes or actions
4. Contradictory statements
5. Anachronisms (events described as past that haven't happened yet)

DOCUMENT EXCERPT (first 3000 chars):
{document_content[:3000]}

THESIS BEING ARGUED:
{thesis}

TODAY'S DATE: November 12, 2025

CRITICAL: Check if the document incorrectly refers to current officials as "former" or uses past tense for ongoing situations.

List any factual errors or concerns you find. If none, respond with "No factual errors detected."

Fact-check results:"""

        try:
            response = self._base_model.invoke(
                [HumanMessage(content=prompt)],
                temperature=0.1,  # Very low for factual analysis
                max_new_tokens=512,
            )

            if hasattr(response, "content") and response.content:
                result = response.content.strip()
                if "no factual errors" in result.lower():
                    return []
                # Parse out individual errors
                errors = [
                    line.strip()
                    for line in result.split("\n")
                    if line.strip() and not line.strip().startswith("#")
                ]
                return errors[:10]  # Limit to top 10 issues
        except Exception as e:
            logger.error(f"[Fact-check] LLM fact-checking failed: {e}")

        return []


    def _apply_factual_corrections(
        self, doc_content: str, factual_errors: list
    ) -> tuple[str, list]:
        """Apply factual corrections to document based on review notes.

        Args:
            doc_content: Current document content
            factual_errors: List of factual error notes from review

        Returns:
            Tuple of (updated_content, revisions_applied)
        """
        revisions = []

        if not factual_errors:
            return doc_content, revisions

        logger.info(
            f"[Phase 1F] Correcting {len(factual_errors)} factual errors"
        )
        self._emit_progress(
            "Phase 1F", f"Correcting {len(factual_errors)} factual errors"
        )

        errors_list = "\n".join(
            [
                f"- {err.replace('FACTUAL ERROR: ', '')}"
                for err in factual_errors
            ]
        )

        correction_prompt = f"""You are editing a research document to fix FACTUAL ERRORS. The following errors were identified:

{errors_list}

TODAY'S DATE: November 12, 2025

DOCUMENT TO CORRECT (showing first 4000 characters):
{doc_content[:4000]}

TASK: Rewrite ONLY the sections that contain factual errors. For each error:
1. Find the incorrect statement in the document
2. Correct it with accurate information
3. Ensure dates, titles, and facts are current and accurate
4. DO NOT change the structure or style, ONLY fix facts

Return the corrected sections in this format:

SECTION: [section name]
CORRECTED TEXT:
[corrected paragraph(s)]
---

Focus ONLY on factual corrections. If you cannot find an error in the excerpt, note it."""

        try:
            response = self._base_model.invoke(
                [HumanMessage(content=correction_prompt)],
                temperature=0.1,
                max_new_tokens=2048,
                repetition_penalty=1.1,
            )

            if hasattr(response, "content") and response.content:
                corrections = response.content.strip()
                correction_blocks = re.findall(
                    r"SECTION:\s*(.+?)\n+CORRECTED TEXT:\s*\n+(.+?)(?=\n---|\Z)",
                    corrections,
                    re.DOTALL | re.IGNORECASE,
                )

                for section_name, corrected_text in correction_blocks:
                    section_name = section_name.strip()
                    section_pattern = (
                        rf"(## {re.escape(section_name)}\n+)(.+?)(?=\n##|\Z)"
                    )
                    section_match = re.search(
                        section_pattern, doc_content, re.DOTALL | re.IGNORECASE
                    )

                    if section_match:
                        logger.info(
                            f"[Phase 1F] Applying fact corrections to {section_name} section"
                        )
                        revisions.append(
                            f"Fact-corrected {section_name} section"
                        )
                    else:
                        logger.warning(
                            f"[Phase 1F] Could not locate section '{section_name}' for correction"
                        )

                logger.info(
                    f"[Phase 1F] Fact-check corrections generated:\n{corrections[:500]}"
                )
                revisions.append(
                    f"Generated fact corrections for {len(correction_blocks)} sections"
                )

        except Exception as e:
            logger.error(
                f"[Phase 1F] Failed to generate fact corrections: {e}"
            )

        return doc_content, revisions

