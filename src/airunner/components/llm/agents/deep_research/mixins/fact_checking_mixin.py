"""Fact-checking mixin for DeepResearchAgent.

Provides fact-checking and correction capabilities for research documents.
"""

import re
import logging
from typing import List, Dict, Tuple
from collections import defaultdict
from datetime import datetime

from langchain_core.messages import HumanMessage, SystemMessage

from airunner.components.llm.tools.research_document_tools import (
    edit_document_find_replace,
)

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

TODAY'S DATE: {datetime.now().strftime('%B %d, %Y')}

INSTRUCTIONS:
1. Verify all dates, titles, and facts against TODAY'S DATE above
2. Check if people are described with correct current titles (e.g., "former" vs "current")
   - Critical: Source documents such as notes may contain results from past events; establish a timeline based on TODAY'S DATE and determine where the sources fit.
   - When establishing timelines, consider the context of topic at hand such as political events, elections, or appointments.
   - Be aware of potential biases in source documents; cross-reference with multiple sources when possible.
   - Look for anachronisms (describing future events as if they already happened, or past events as if they're current)
   - Verify job titles match the timeframe being discussed
   - Check if timelines and sequences of events are logically consistent
   - IMPORTANT: If a source is dated in the past (e.g., 2024) but the current date is 2025, DO NOT flag it as "not yet published" or "irrelevant". It is a past source.
   - IMPORTANT: If a source discusses a "future" event that is now in the past relative to TODAY'S DATE, treat it as a historical record of that prediction/plan.
3. Ensure all claims are supported by credible sources
   - Rank the credibility of sources if possible
   - Cross-check facts against multiple sources to ensure accuracy

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

                # Parse out individual errors, filtering garbage
                errors = []
                for line in result.split("\n"):
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    # Skip lines that look like instructions/meta-commentary
                    if any(
                        x in line
                        for x in [
                            "FACTUAL ERROR in",
                            "Wrong job titles",
                            "Misattributed quotes",
                            "Contradictory statements",
                            "Anachronisms",
                            "To revise the section",
                            "However, there are some",
                            "general suggestions",
                            "I did not find",
                            "The document does not",
                        ]
                    ):
                        continue
                    # Only add if it looks like an actual error description
                    if len(line) > 10 and not line.endswith(":"):
                        errors.append(line)

                return errors[:10]  # Limit to top 10 issues
        except Exception as e:
            logger.error(f"[Fact-check] LLM fact-checking failed: {e}")

        return []

    def _apply_factual_corrections(
        self, doc_content: str, factual_errors: list
    ) -> tuple[str, list]:
        """Apply factual corrections to document based on review notes."""
        revisions = []
        if not factual_errors:
            return doc_content, revisions

        logger.info(
            f"[Phase 1F] Correcting {len(factual_errors)} factual errors"
        )
        self._emit_progress(
            "Phase 1F", f"Correcting {len(factual_errors)} factual errors"
        )

        correction_prompt = self._build_correction_prompt(
            doc_content, factual_errors
        )

        try:
            corrections = self._generate_corrections_with_llm(
                correction_prompt
            )
            if corrections:
                correction_blocks = self._parse_correction_blocks(corrections)
                doc_content, revisions = self._apply_correction_blocks(
                    doc_content, correction_blocks
                )
        except Exception as e:
            logger.error(
                f"[Phase 1F] Failed to generate fact corrections: {e}"
            )

        return doc_content, revisions

    def _build_correction_prompt(
        self, doc_content: str, factual_errors: list
    ) -> str:
        """Build prompt for factual corrections."""
        errors_list = "\n".join(
            [
                f"- {err.replace('FACTUAL ERROR: ', '')}"
                for err in factual_errors
            ]
        )

        return f"""You are editing a research document to fix FACTUAL ERRORS. The following errors were identified:

{errors_list}

TODAY'S DATE: {datetime.now().strftime('%B %d, %Y')}

DOCUMENT TO CORRECT (showing first 4000 characters):
{doc_content[:4000]}

TASK: Rewrite ONLY the sections that contain factual errors. For each error:
1. Find the incorrect statement in the document
2. Correct it with accurate information
3. Ensure dates, titles, and facts stay aligned with the timeframe established in the research notes
    - CRITICAL: Keep official titles exactly as they appear in the supporting evidence; do not assume present-day offices.
4. DO NOT change the structure or style, ONLY fix facts
5. DO NOT include any conversational text, "Here is the corrected text", or reasoning.
6. OUTPUT ONLY THE FORMAT BELOW.

Return the corrected sections in this format:

SECTION: [section name]
CORRECTED TEXT:
[corrected paragraph(s)]
---

Focus ONLY on factual corrections. If you cannot find an error in the excerpt, note it."""

    def _generate_corrections_with_llm(self, prompt: str) -> str | None:
        """Generate corrections using LLM."""
        response = self._base_model.invoke(
            [HumanMessage(content=prompt)],
            temperature=0.1,
            max_new_tokens=2048,
            repetition_penalty=1.1,
        )

        if hasattr(response, "content") and response.content:
            return response.content.strip()
        return None

    def _parse_correction_blocks(self, corrections: str) -> list:
        """Parse correction blocks from LLM response."""
        import re

        return re.findall(
            r"SECTION:\s*(.+?)\n+CORRECTED TEXT:\s*\n+(.+?)(?=\n---|\Z)",
            corrections,
            re.DOTALL | re.IGNORECASE,
        )

    def _apply_correction_blocks(
        self, doc_content: str, correction_blocks: list
    ) -> tuple[str, list]:
        """Apply correction blocks to document.

        Returns:
            (modified_doc_content, revisions_list)
        """
        import re

        revisions = []
        for section_name, corrected_text in correction_blocks:
            section_name = section_name.strip()
            corrected_text = corrected_text.strip()

            # Pattern to match section header + content
            section_pattern = (
                rf"(## {re.escape(section_name)}\n+)(.+?)(?=\n##|\Z)"
            )
            section_match = re.search(
                section_pattern, doc_content, re.DOTALL | re.IGNORECASE
            )

            if section_match:
                # Replace the section content with corrected version
                old_section = section_match.group(0)
                new_section = section_match.group(1) + corrected_text + "\n\n"
                doc_content = doc_content.replace(old_section, new_section, 1)

                logger.info(
                    f"[Phase 1F] Applied fact corrections to {section_name} section"
                )
                revisions.append(f"Fact-corrected {section_name} section")
            else:
                logger.warning(
                    f"[Phase 1F] Could not locate section '{section_name}' for correction"
                )

        if revisions:
            logger.info(
                f"[Phase 1F] Applied {len(revisions)} fact corrections"
            )

        return doc_content, revisions

    # ==================================================================
    # INTELLIGENT SECTION-LEVEL REVISION
    # ==================================================================

    def _group_review_notes_by_section(
        self, review_notes: list, doc_content: str
    ) -> Dict[str, List[str]]:
        """Group review notes by the section they refer to.

        Args:
            review_notes: List of all review issues found
            doc_content: Full document content

        Returns:
            Dict mapping section names to list of issues for that section
        """
        # Extract section names from document
        section_pattern = r"^## (.+)$"
        sections = re.findall(section_pattern, doc_content, re.MULTILINE)

        grouped = defaultdict(list)

        for note in review_notes:
            # Try to identify which section this note refers to
            section_found = False
            note_lower = note.lower()

            # First, check for explicit section markers like "in 'Section Name'"
            for section in sections:
                section_lower = section.lower()
                # Check multiple patterns
                if any(
                    [
                        f"in '{section_lower}'" in note_lower,
                        f'in "{section_lower}"' in note_lower,
                        f"section: {section_lower}" in note_lower,
                        f"{section_lower} section" in note_lower,
                        # Partial match for longer section names
                        section_lower in note_lower
                        and len(section_lower) > 10,
                        # Exact match for shorter names
                        (
                            section == note.split(":")[0].strip()
                            if ":" in note
                            else False
                        ),
                    ]
                ):
                    grouped[section].append(note)
                    section_found = True
                    break

            # Only mark as general if it's truly a structural issue
            if not section_found:
                # These are genuinely general issues
                if any(
                    [
                        "missing section" in note_lower,
                        "only " in note_lower and "sources" in note_lower,
                        "temporal" in note_lower and "issue" in note_lower,
                        "sources section" in note_lower,
                        "empty sources" in note_lower,
                        "few sources" in note_lower,
                    ]
                ):
                    grouped["_general_"].append(note)
                else:
                    # Default to first substantive section for other issues
                    # (better to over-revise than under-revise)
                    substantive_sections = [
                        s
                        for s in sections
                        if s
                        not in ["Sources", "Table of Contents", "Abstract"]
                    ]
                    if substantive_sections:
                        grouped[substantive_sections[0]].append(note)
                    else:
                        grouped["_general_"].append(note)

        return dict(grouped)

    def _revise_section_with_context(
        self,
        section_name: str,
        section_content: str,
        issues: List[str],
        notes_path: str,
    ) -> str | None:
        """Revise a single section using RAG context and verification.

        Args:
            section_name: Name of the section to revise
            section_content: Current content of the section
            issues: List of issues found in this section
            notes_path: Path to research notes for RAG queries

        Returns:
            Revised section content, or None if revision failed
        """
        logger.info(
            f"[Phase 1F] Revising {section_name} with {len(issues)} issues"
        )

        # Query RAG for relevant context about this section's topic
        try:
            rag_context = self._query_rag_for_section_revision(
                section_name, section_content, notes_path
            )
            logger.info(
                f"[Phase 1F] RAG query successful for {section_name}, got {len(rag_context)} chars"
            )
        except Exception as e:
            logger.error(
                f"[Phase 1F] RAG query failed for {section_name}: {e}",
                exc_info=True,
            )
            rag_context = (
                "No additional context available from research notes."
            )

        # Build revision prompt with RAG context
        try:
            revision_prompt = self._build_section_revision_prompt(
                section_name, section_content, issues, rag_context
            )
            logger.info(
                f"[Phase 1F] Built revision prompt for {section_name}, {len(revision_prompt)} chars"
            )
        except Exception as e:
            logger.error(
                f"[Phase 1F] Failed to build prompt for {section_name}: {e}",
                exc_info=True,
            )
            return None

        try:
            # Generate revised section
            logger.info(f"[Phase 1F] Calling LLM to revise {section_name}...")

            messages = [HumanMessage(content=revision_prompt)]
            system_prompt = (
                self._get_synthesis_system_prompt()
                if hasattr(self, "_get_synthesis_system_prompt")
                else getattr(self, "_synthesis_system_prompt", None)
            )
            if not system_prompt:
                system_prompt = getattr(self, "_system_prompt", None)
            if system_prompt:
                messages.insert(0, SystemMessage(content=system_prompt))

            response = self._base_model.invoke(
                messages,
                temperature=0.2,  # Low temp for accuracy
                max_new_tokens=2048,
                repetition_penalty=1.1,
            )
            logger.info(f"[Phase 1F] LLM response received for {section_name}")

            if hasattr(response, "content") and response.content:
                revised = response.content.strip()
                logger.info(
                    f"[Phase 1F] Got revised content for {section_name}, {len(revised)} chars"
                )

                # Clean up markdown formatting artifacts
                revised = re.sub(r"^```(?:markdown)?\n", "", revised)
                revised = re.sub(r"\n```$", "", revised)

                # Remove any explanatory notes/meta-commentary that slipped through
                # Remove "Note:" sections at the end
                revised = re.sub(
                    r"\n+Note:.*$",
                    "",
                    revised,
                    flags=re.DOTALL | re.IGNORECASE,
                )
                # Remove "Revised Section:" prefix
                revised = re.sub(
                    r"^(?:Revised Section|SECTION):\s*\w+\s*\n+",
                    "",
                    revised,
                    flags=re.IGNORECASE,
                )
                # Remove "I made the following changes:" style notes
                revised = re.sub(
                    r"\n+I (?:made|have made) the following changes?:.*$",
                    "",
                    revised,
                    flags=re.DOTALL | re.IGNORECASE,
                )
                # Remove bullet lists of changes at the end
                revised = re.sub(
                    r"\n+(?:Changes made|Revisions|Corrections):.*$",
                    "",
                    revised,
                    flags=re.DOTALL | re.IGNORECASE,
                )

                # Remove "Revision Notes" or similar headers that might appear
                revised = re.sub(
                    r"\n+##? Revision Notes.*$",
                    "",
                    revised,
                    flags=re.DOTALL | re.IGNORECASE,
                )

                # CRITICAL: Remove any fact-check contamination that leaked through
                # Remove lines starting with numbered fact errors
                revised = re.sub(
                    r"^\d+\.\s*FACTUAL ERROR.*?$",
                    "",
                    revised,
                    flags=re.MULTILINE,
                )
                # Remove any standalone "FACTUAL ERROR" lines
                revised = re.sub(
                    r"^\s*FACTUAL ERROR.*?$",
                    "",
                    revised,
                    flags=re.MULTILINE | re.IGNORECASE,
                )
                # Remove "To revise the section" instructions
                revised = re.sub(
                    r"^\s*To revise the section.*?$",
                    "",
                    revised,
                    flags=re.MULTILINE | re.IGNORECASE,
                )
                # Remove "Wrong job titles" comments
                revised = re.sub(
                    r"^\s*Wrong job titles.*?$",
                    "",
                    revised,
                    flags=re.MULTILINE | re.IGNORECASE,
                )

                # CRITICAL: Remove numbered instruction lists at the beginning
                # These are the LLM's internal planning, not content
                # Pattern: "1. Do X\n2. Do Y\n...\n\nHere is the rewritten section:"
                revised = re.sub(
                    r"^(?:\d+\.\s+.+?\n){2,}.*?(?:here is|here's|below is|rewritten section|revised section).*?\n+",
                    "",
                    revised,
                    flags=re.IGNORECASE | re.DOTALL,
                )

                # Remove any remaining "phrases like" style instruction fragments
                revised = re.sub(
                    r"^.*?phrases like.*?\n", "", revised, flags=re.IGNORECASE
                )

                # Remove "Remove redundant phrases" instructions
                revised = re.sub(
                    r"^\d+\.\s+Remove.*?\n",
                    "",
                    revised,
                    flags=re.MULTILINE | re.IGNORECASE,
                )

                # Remove conversational preambles (e.g. "Here is the revised section:")
                # Must come AFTER the numbered list removal
                conversational_patterns = [
                    r"^.*?here is the (?:revised|rewritten|corrected) section.*?:\s*\n+",
                    r"^.*?here's the (?:revised|rewritten|corrected) section.*?:\s*\n+",
                    r"^.*?below is the (?:revised|rewritten|corrected) section.*?:\s*\n+",
                    r"^.*?(?:revised|rewritten|corrected) section below.*?:\s*\n+",
                    r"^.*?please correct the issues.*?(?:revised|corrected) text.*?:\s*\n+",
                    r"^please correct the issues.*?\n+",
                ]
                for pattern in conversational_patterns:
                    revised = re.sub(
                        pattern, "", revised, flags=re.IGNORECASE | re.DOTALL
                    )

                # If it still doesn't start with the section title or substantial content,
                # try to find where the real content starts
                if not revised.strip().startswith(
                    ("During", "In ", "The ", "President", "According")
                ):
                    # Look for the first substantial paragraph (3+ words starting with capital)
                    match = re.search(
                        r"\n\n([A-Z][a-z]+(?:\s+[A-Za-z]+){2,})", revised
                    )
                    if match:
                        # Start from this point
                        revised = revised[match.start(1) :]

                # CRITICAL VALIDATION: Check if LLM returned error list instead of revised content
                # If the output contains multiple lines starting with numbers and "FACTUAL ERROR", reject it
                factual_error_lines = len(
                    re.findall(
                        r"^\s*\d+\.\s*FACTUAL ERROR", revised, re.MULTILINE
                    )
                )
                if factual_error_lines >= 3:
                    logger.error(
                        f"[Phase 1F] LLM returned error list instead of revised content for {section_name}, rejecting"
                    )
                    return None  # Reject this revision entirely

                # Additional validation: If output is mostly numbers/bullets describing errors, reject
                if revised.count("FACTUAL ERROR") > 2:
                    logger.error(
                        f"[Phase 1F] LLM output contains repeated 'FACTUAL ERROR' markers for {section_name}, rejecting"
                    )
                    return None

                # CRITICAL: Check if output contains planning/instruction text that wasn't filtered
                planning_indicators = [
                    "phrases like",
                    "remove redundant",
                    "here is the rewritten section",
                    "here is the revised section",
                    r"\d+\.\s+(?:Remove|Ensure|Maintain|Do not|Keep)",  # Numbered instructions
                ]
                for indicator in planning_indicators:
                    if re.search(indicator, revised, re.IGNORECASE):
                        logger.error(
                            f"[Phase 1F] LLM output contains planning/instruction text for {section_name}, rejecting"
                        )
                        logger.error(
                            f"[Phase 1F] Found indicator: {indicator}"
                        )
                        logger.error(
                            f"[Phase 1F] First 200 chars: {revised[:200]}"
                        )
                        return None  # Reject - LLM didn't follow instructions

                cleaned = revised.strip()
                logger.info(
                    f"[Phase 1F] Cleaned revision for {section_name}, final {len(cleaned)} chars"
                )
                return cleaned
            else:
                logger.warning(
                    f"[Phase 1F] LLM response has no content for {section_name}"
                )
        except Exception as e:
            logger.error(
                f"[Phase 1F] Failed to revise {section_name}: {e}",
                exc_info=True,
            )

        return None

    def _query_rag_for_section_revision(
        self, section_name: str, section_content: str, notes_path: str
    ) -> str:
        """Query RAG for context to help revise a section.

        Args:
            section_name: Name of section being revised
            section_content: Current section content
            notes_path: Path to notes file

        Returns:
            RAG context string
        """
        logger.info(f"[Phase 1F] Starting RAG query for {section_name}")
        try:
            # API IS the RAG manager (LLMModelManager inherits from RAGMixin)
            rag_manager = self._api if self._api else None
            logger.info(
                f"[Phase 1F] RAG manager exists: {rag_manager is not None}"
            )

            if not rag_manager or not hasattr(rag_manager, "search"):
                logger.warning(
                    f"[Phase 1F] No RAG manager available for {section_name} (has search: {hasattr(rag_manager, 'search') if rag_manager else False})"
                )
                return "No additional context available from research notes."

            # Ensure notes are loaded into RAG
            logger.info(
                f"[Phase 1F] Attempting to load notes from {notes_path}"
            )
            try:
                if hasattr(rag_manager, "ensure_indexed_files"):
                    rag_manager.ensure_indexed_files([notes_path])
                    logger.info(
                        f"[Phase 1F] Loaded notes into RAG via ensure_indexed_files"
                    )
                elif hasattr(self, "_load_notes_into_rag"):
                    self._load_notes_into_rag(notes_path)
                    logger.info(
                        f"[Phase 1F] Loaded notes into RAG via _load_notes_into_rag"
                    )
                else:
                    logger.warning(
                        f"[Phase 1F] No method available to load notes into RAG"
                    )
            except Exception as e:
                logger.warning(
                    f"[Phase 1F] Failed to load notes into RAG: {e}",
                    exc_info=True,
                )

            # Extract key topics from section content for query
            query_text = f"{section_name}: {section_content[:500]}"
            logger.info(
                f"[Phase 1F] Executing RAG search with query length {len(query_text)}"
            )

            # Query RAG using the search method
            results = rag_manager.search(query_text, k=5)
            logger.info(
                f"[Phase 1F] RAG search returned {len(results) if results else 0} results"
            )

            if results:
                context_parts = []
                for i, doc in enumerate(results, 1):
                    # Try multiple attribute names for content
                    content = ""
                    if hasattr(doc, "page_content"):
                        content = (
                            doc.page_content.strip()
                            if doc.page_content
                            else ""
                        )
                    elif hasattr(doc, "text"):
                        content = doc.text.strip() if doc.text else ""
                    elif hasattr(doc, "content"):
                        content = doc.content.strip() if doc.content else ""

                    # Debug: log document structure if content is empty
                    if not content:
                        logger.warning(
                            f"[Phase 1F] RAG doc {i} has no content. Type: {type(doc)}, attrs: {dir(doc)[:10]}"
                        )

                    if content:
                        context_parts.append(f"[Source {i}]\n{content}")

                context = "\n\n".join(context_parts)
                logger.info(
                    f"[Phase 1F] Retrieved {len(results)} RAG chunks for {section_name}, {len(context_parts)} with content, total {len(context)} chars"
                )

                if context:
                    return f"Relevant research notes:\n{context}"
                else:
                    logger.warning(
                        f"[Phase 1F] RAG returned {len(results)} results but all had empty content"
                    )
                    return (
                        "No additional context available from research notes."
                    )
            else:
                logger.warning(f"[Phase 1F] No RAG results for {section_name}")
        except Exception as e:
            logger.error(
                f"[Phase 1F] RAG query failed for {section_name}: {e}",
                exc_info=True,
            )

        return "No additional context available from research notes."

    def _build_section_revision_prompt(
        self,
        section_name: str,
        section_content: str,
        issues: List[str],
        rag_context: str,
    ) -> str:
        """Build prompt for revising a single section.

        Args:
            section_name: Section being revised
            section_content: Current content
            issues: Issues to fix
            rag_context: Context from RAG

        Returns:
            Revision prompt
        """
        # Clean issues list - remove metadata prefixes like "FACTUAL ERROR in 'Section':"
        cleaned_issues = []
        for issue in issues:
            # Extract just the error description, removing section attribution
            cleaned = re.sub(
                r"^(?:FACTUAL ERROR|TEMPORAL ISSUE|STYLE|MISSING SECTION|DUPLICATE SECTIONS|EMPTY SOURCES|FEW SOURCES) in ['\"]?[^:]+['\"]?:\s*",
                "",
                issue,
            )
            cleaned = re.sub(
                r"^(?:FACTUAL ERROR|TEMPORAL ISSUE|STYLE|MISSING SECTION|DUPLICATE SECTIONS|EMPTY SOURCES|FEW SOURCES):\s*",
                "",
                cleaned,
            )
            cleaned_issues.append(cleaned.strip())

        issues_text = "\n".join(
            [
                f"{i+1}. {issue}"
                for i, issue in enumerate(cleaned_issues)
                if issue
            ]
        )

        return f"""Fix the issues in this section and return ONLY the corrected text.

SECTION TO REVISE:
{section_content}

ISSUES TO FIX:
{issues_text}

RESEARCH CONTEXT:
{rag_context}

CRITICAL RULES:
1. Return ONLY the revised section text - NO explanations, NO notes, NO preambles
2. Do NOT say "Here is the revised section" or similar - just return the text itself
3. Do NOT list what you changed - just return the corrected content
4. Preserve historical titles and dates - if something was "Former President" in 2024, keep it that way
5. Fix only actual factual errors, not style or temporal context
6. Start your response with the actual section content, not with meta-commentary

BEGIN REVISED SECTION BELOW (text only, no preamble):
"""

    def _apply_section_revisions(
        self,
        doc_content: str,
        section_revisions: Dict[str, str],
        document_path: str = None,
    ) -> Tuple[str, List[str]]:
        """Apply revised sections to document.

        Args:
            doc_content: Full document content
            section_revisions: Dict mapping section names to revised content
            document_path: Optional path to document file. If provided, uses edit_document_find_replace tool.

        Returns:
            (modified_doc_content, list_of_applied_revisions)
        """
        revisions_applied = []

        for section_name, revised_content in section_revisions.items():
            if section_name == "_general_":
                continue  # Skip general issues for now

            # Find and replace the section
            section_pattern = (
                rf"(## {re.escape(section_name)}\n+)(.+?)(?=\n##|\Z)"
            )
            match = re.search(section_pattern, doc_content, re.DOTALL)

            if match:
                old_section = match.group(0)
                new_section = match.group(1) + revised_content.strip() + "\n\n"

                if document_path:
                    try:
                        # Use the tool to update the file
                        edit_document_find_replace(
                            document_path,
                            old_section,
                            new_section,
                            is_regex=False,
                            api=self._api if hasattr(self, "_api") else None,
                        )
                        # Update memory content to match file
                        doc_content = doc_content.replace(
                            old_section, new_section, 1
                        )
                        revisions_applied.append(
                            f"Revised {section_name} section"
                        )
                        logger.info(
                            f"[Phase 1F] Applied revision to {section_name} using tool"
                        )
                    except Exception as e:
                        logger.error(
                            f"[Phase 1F] Failed to apply revision with tool: {e}"
                        )
                        # Fallback to memory update only (will be saved later if save is called)
                        doc_content = doc_content.replace(
                            old_section, new_section, 1
                        )
                        revisions_applied.append(
                            f"Revised {section_name} section (memory only)"
                        )
                else:
                    doc_content = doc_content.replace(
                        old_section, new_section, 1
                    )
                    revisions_applied.append(f"Revised {section_name} section")
                    logger.info(
                        f"[Phase 1F] Applied revision to {section_name}"
                    )
            else:
                logger.warning(
                    f"[Phase 1F] Could not find section {section_name}"
                )

        return doc_content, revisions_applied

    def _validate_revisions(
        self, doc_content: str, original_issues: list, notes_path: str
    ) -> list:
        """Validate that revisions actually fixed the reported issues.

        Args:
            doc_content: Revised document content
            original_issues: Original list of issues found
            notes_path: Path to research notes for context

        Returns:
            List of issues that are still present after revision
        """
        logger.info("[Phase 1F] Validating revisions...")

        # Extract key patterns from original issues to check if they're fixed
        remaining_issues = []

        for issue in original_issues:
            issue_lower = issue.lower()

            # Check for specific common issues that can be validated
            if (
                "former president" in issue_lower
                and "former president" in doc_content.lower()
            ):
                # Issue claimed "former" is wrong, but it's still there
                remaining_issues.append(issue)
            elif "missing section" in issue_lower:
                # Check if the section was added
                section_match = re.search(
                    r"missing section[:\s]+([\w\s]+)", issue_lower
                )
                if section_match:
                    section_name = section_match.group(1).strip()
                    if f"## {section_name}" not in doc_content.lower():
                        remaining_issues.append(issue)
            elif (
                "only 0 sources" in issue_lower
                or "empty sources" in issue_lower
            ):
                # Check if sources were added
                sources_match = re.search(
                    r"## Sources\s+(.+?)(?=\n##|\Z)",
                    doc_content,
                    re.DOTALL | re.IGNORECASE,
                )
                if sources_match:
                    sources_content = sources_match.group(1).strip()
                    # If sources section is still very short, issue persists
                    if len(sources_content) < 100:
                        remaining_issues.append(issue)
                else:
                    remaining_issues.append(issue)

        return remaining_issues
