"""Review phase mixin for DeepResearchAgent.

Handles Phase 1E and 1F: reviewing document quality, applying corrections, and finalizing.
"""

import os
import re
import logging
from pathlib import Path
from typing import TypedDict
from datetime import datetime

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
    review_notes: list  # Added: issues found in Phase 1E
    revisions_applied: list  # Added: revisions applied in Phase 1F


class ReviewPhaseMixin:
    """Provides Phase 1E and 1F review, revision, and finalization methods."""

    def _phase1e_review(self, state: DeepResearchState) -> dict:
        """Phase 1E: Review and validate document quality."""
        document_path = state.get("document_path", "")
        notes_path = state.get("notes_path", "")
        thesis = state.get("thesis_statement", "")

        logger.info(
            f"[Phase 1E] Reviewing document for quality AND factual accuracy"
        )
        self._emit_progress("Phase 1E", "Reviewing document quality and facts")

        # Validate document exists
        doc_content = self._load_document_for_review(document_path)
        if not doc_content:
            return self._review_skip_state(state)

        # Perform all review checks
        review_notes = self._perform_review_checks(
            doc_content, thesis, document_path, notes_path
        )

        # Add style checking for redundancy and clichés
        style_issues = self._check_writing_style(doc_content)
        if style_issues:
            review_notes.extend(style_issues)
            logger.info(
                f"[Phase 1E] Found {len(style_issues)} style issues (redundancy/clichés)"
            )

        # Log and emit results
        self._finalize_review(review_notes)

        return {
            "messages": state.get("messages", []),
            "review_notes": review_notes,
            "current_phase": "phase1f",
        }

    def _load_document_for_review(self, document_path: str) -> str | None:
        """Load document content for review."""
        if not document_path or not Path(document_path).exists():
            logger.error(f"[Phase 1E] Document not found: {document_path}")
            return None

        try:
            with open(document_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            logger.error(f"[Phase 1E] Failed to read document: {e}")
            return None

    def _review_skip_state(self, state: DeepResearchState) -> dict:
        """Return state when skipping review."""
        return {
            "messages": state.get("messages", []),
            "current_phase": "phase1f",
        }

    def _perform_review_checks(
        self,
        doc_content: str,
        thesis: str,
        document_path: str,
        notes_path: str = "",
    ) -> list:
        """Perform all review checks on document."""
        review_notes = []

        # Check for required sections
        review_notes.extend(self._check_required_sections(doc_content))

        # Check content quality
        review_notes.extend(self._check_content_quality(doc_content))

        # Check for temporal references (NEW)
        review_notes.extend(self._check_temporal_references(doc_content))

        # Check for proper sources section and validate citations (NEW)
        review_notes.extend(
            self._check_sources_section(doc_content, notes_path)
        )

        # Check for raw notes
        if self._contains_raw_notes(doc_content):
            review_notes.append("Document may contain unprocessed raw notes")
            logger.warning(f"[Phase 1E] Found potential raw notes markers")

        # Fact-check (systematic chunk-by-chunk review)
        review_notes.extend(self._fact_check_systematic(doc_content, thesis))

        return review_notes

    def _check_required_sections(self, doc_content: str) -> list:
        """Check for required sections."""
        review_notes = []
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
        return review_notes

    def _check_content_quality(self, doc_content: str) -> list:
        """Check content quality metrics."""
        review_notes = []

        # Check length
        if len(doc_content) < 1000:
            review_notes.append("Document is too short")
            logger.warning(
                f"[Phase 1E] Document only {len(doc_content)} chars"
            )

        # Check source citations
        source_count = len(re.findall(r"\*\*Source \d+\*\*", doc_content))
        if source_count < 3:
            review_notes.append(
                f"Only {source_count} sources cited - expected more"
            )
            logger.warning(f"[Phase 1E] Only {source_count} sources found")

        return review_notes

    def _contains_raw_notes(self, doc_content: str) -> bool:
        """Check if document contains unprocessed notes markers."""
        return bool(re.search(r"###\s+https?://", doc_content))

    def _check_temporal_references(self, doc_content: str) -> list:
        """Check for inappropriate temporal references like 'former president' for historical roles.

        CRITICAL: Research documents should use timeless language. When describing actions
        that occurred while someone held a specific office, refer to that role directly unless
        the contrast between time periods is the point of the sentence.
        """
        review_notes = []

        # Common temporal issues
        temporal_patterns = [
            (
                r"former [Pp]resident",
                "Use 'President' (timeless in historical context)",
            ),
            (
                r"former [Pp]rime [Mm]inister",
                "Use 'Prime Minister' (timeless in historical context)",
            ),
            (
                r"former [Gg]overnor",
                "Use 'Governor' (timeless in historical context)",
            ),
            (
                r"currently|at present|right now|these days",
                "Avoid temporal markers - use timeless language",
            ),
            (
                r"recently announced|just released|has just",
                "Use past tense without temporal markers",
            ),
        ]

        for pattern, issue in temporal_patterns:
            matches = re.findall(pattern, doc_content, re.IGNORECASE)
            if matches:
                review_notes.append(
                    f"TEMPORAL ISSUE: {issue} (found {len(matches)} instance(s))"
                )
                logger.warning(
                    f"[Phase 1E] Temporal reference issue: {matches[0]} - {issue}"
                )

        return review_notes

    def _fix_temporal_references(self, doc_content: str) -> str:
        """Apply global fixes for temporal reference issues.

        This directly fixes common temporal issues like 'former President'
        that should be 'President' in historical research context.
        """
        # Fix 'former President' -> 'President' (preserving capitalization)
        doc_content = re.sub(
            r"\bformer President(?=\s+[A-Z])", "President", doc_content
        )
        doc_content = re.sub(
            r"\bformer president(?=\s+[A-Z])", "president", doc_content
        )

        # Fix 'former Prime Minister' -> 'Prime Minister'
        doc_content = re.sub(
            r"\bformer Prime Minister(?=\s+[A-Z])",
            "Prime Minister",
            doc_content,
        )

        # Fix 'former Governor' -> 'Governor'
        doc_content = re.sub(
            r"\bformer Governor(?=\s+[A-Z])", "Governor", doc_content
        )

        logger.info("[Phase 1F] Applied temporal reference fixes")
        return doc_content

    def _check_sources_section(
        self, doc_content: str, notes_path: str = ""
    ) -> list:
        """Check if Sources section exists and is properly populated."""
        review_notes = []

        # Check if Sources section exists
        # Note: We check for "## Sources" but also handle duplicate sections in formatting mixin
        if "## Sources" not in doc_content:
            review_notes.append("MISSING SECTION: Sources section is required")
            logger.warning(f"[Phase 1E] No Sources section found")
            return review_notes

        # Extract Sources section content - find the LAST one if duplicates exist
        sources_matches = list(
            re.finditer(
                r"## Sources\s*\n+(.*?)(?:\n##|$)", doc_content, re.DOTALL
            )
        )

        if sources_matches:
            # Check if we have multiple source sections
            if len(sources_matches) > 1:
                review_notes.append(
                    "DUPLICATE SECTIONS: Multiple 'Sources' sections found"
                )

            # Validate the content of the last one (most likely the real one)
            sources_content = sources_matches[-1].group(1).strip()

            # Check if it's empty or just placeholder text
            if len(sources_content) < 50:
                review_notes.append(
                    "EMPTY SOURCES: Sources section exists but is empty or minimal"
                )
                logger.warning(
                    f"[Phase 1E] Sources section is too short: {len(sources_content)} chars"
                )

            # Check if it contains actual URLs
            urls_found = len(re.findall(r"https?://", sources_content))
            if urls_found < 3:
                review_notes.append(
                    f"FEW SOURCES: Only {urls_found} source URLs found - expected 5+"
                )
                logger.warning(
                    f"[Phase 1E] Only {urls_found} URLs in Sources section"
                )

            # CRITICAL: Check for hallucinated/fake URLs that don't appear in notes
            # Extract all URLs from sources section
            source_urls = set(
                re.findall(r'https?://[^\s<>"{}|\\^`\[\]]+', sources_content)
            )
            if source_urls and notes_path:
                logger.info(
                    f"[Phase 1E] Found {len(source_urls)} URLs in Sources section, validating against notes..."
                )
                citation_warnings = self._validate_citations_against_notes(
                    source_urls, notes_path
                )
                review_notes.extend(citation_warnings)

        return review_notes

    def _validate_citations_against_notes(
        self, source_urls: set, notes_path: str
    ) -> list:
        """Validate that citations in Sources section actually appear in research notes.

        Args:
            source_urls: Set of URLs found in Sources section
            notes_path: Path to .notes.md file

        Returns:
            List of fake/hallucinated URL warnings
        """
        warnings = []

        if not notes_path or not os.path.exists(notes_path):
            logger.warning(
                f"[Phase 1E] Cannot validate citations - notes file not found: {notes_path}"
            )
            return warnings

        try:
            with open(notes_path, "r", encoding="utf-8") as f:
                notes_content = f.read()

            # Extract all URLs that actually appear in notes
            actual_urls = set(
                re.findall(r'https?://[^\s<>"{}|\\^`\[\]]+', notes_content)
            )

            # Check which source URLs are not in notes (potential hallucinations)
            fake_urls = source_urls - actual_urls

            if fake_urls:
                logger.warning(
                    f"[Phase 1E] Found {len(fake_urls)} potentially fabricated URLs in Sources section"
                )
                for url in list(fake_urls)[:5]:  # Report first 5
                    warnings.append(
                        f"FAKE CITATION: URL not found in research notes: {url}"
                    )
                    logger.warning(f"[Phase 1E] Fake citation detected: {url}")

        except Exception as e:
            logger.error(f"[Phase 1E] Failed to validate citations: {e}")

        return warnings

    def _fact_check_systematic(self, doc_content: str, thesis: str) -> list:
        """Run fact-checking systematically through document in batches.

        This checks multiple sections in batched LLM calls for efficiency.
        """
        review_notes = []

        # Split document into sections
        sections = re.split(r"\n##\s+", doc_content)

        # Prepare sections for batch fact-checking (limit to first 6)
        sections_to_check = []
        sections_to_check_metadata = []

        for i, section in enumerate(
            sections[:7]
        ):  # +1 because first split is usually header
            if len(section.strip()) < 200:  # Skip very short sections
                continue

            # Skip Sources, Abstract, TOC
            first_line = section.split("\n")[0].strip()
            if any(
                x in first_line
                for x in ["Sources", "Abstract", "Table of Contents"]
            ):
                continue

            chunk_to_check = section[:2000]  # 2000 chars per section
            section_name = first_line[:50]
            sections_to_check.append(chunk_to_check)
            sections_to_check_metadata.append(section_name)

        if not sections_to_check:
            return review_notes

        # Batch fact-check in groups of 3 to balance speed and quality
        batch_size = 3
        for batch_idx in range(0, len(sections_to_check), batch_size):
            batch = sections_to_check[batch_idx : batch_idx + batch_size]
            batch_meta = sections_to_check_metadata[
                batch_idx : batch_idx + batch_size
            ]

            logger.info(
                f"[Phase 1E] Batch fact-checking sections {batch_idx+1}-{batch_idx+len(batch)}: {batch_meta}"
            )
            self._emit_progress(
                "Phase 1E",
                f"Fact-checking batch {batch_idx // batch_size + 1}",
            )

            # Batch fact-check these sections together
            batch_errors = self._fact_check_batch(batch, batch_meta, thesis)
            review_notes.extend(batch_errors)

        logger.info(
            f"[Phase 1E] Batch fact-check found {len(review_notes)} issues"
        )
        return review_notes

    def _fact_check_batch(
        self, sections: list, section_names: list, thesis: str
    ) -> list:
        """Fact-check multiple sections in a single LLM call.

        Args:
            sections: List of section contents to check
            section_names: List of section names
            thesis: The thesis statement

        Returns:
            List of error entries with section attribution
        """
        # Build combined prompt for batch
        sections_text = ""
        for i, (section_name, section_content) in enumerate(
            zip(section_names, sections)
        ):
            sections_text += (
                f"\n\n### SECTION {i+1}: {section_name}\n{section_content}\n"
            )

        prompt = f"""You are a fact-checking expert reviewing a research paper. Carefully examine the following sections for FACTUAL ERRORS.

THESIS: {thesis}
TODAY'S DATE: {datetime.now().strftime('%B %d, %Y')}

SECTIONS TO CHECK:{sections_text}

For EACH section with errors, format your response as:
SECTION [number]: [error description]

If a section has no errors, skip it. If ALL sections are error-free, respond with "No factual errors detected."

Fact-check results:"""

        try:
            from langchain_core.messages import HumanMessage

            response = self._base_model.invoke(
                [HumanMessage(content=prompt)],
                temperature=0.1,
                max_new_tokens=1024,  # More tokens for batch
            )

            if hasattr(response, "content") and response.content:
                result = response.content.strip()
                if "no factual errors" in result.lower():
                    return []

                # Parse batch results
                errors = []
                for line in result.split("\n"):
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue

                    # Try to extract section number and assign to correct section
                    if line.startswith("SECTION "):
                        # Format: "SECTION 1: error description"
                        match = re.match(r"SECTION (\d+):\s*(.+)", line)
                        if match:
                            section_idx = int(match.group(1)) - 1
                            error_desc = match.group(2).strip()
                            if 0 <= section_idx < len(section_names):
                                error_entry = f"FACTUAL ERROR in '{section_names[section_idx]}': {error_desc}"
                                errors.append(error_entry)
                    elif len(line) > 10 and not line.endswith(":"):
                        # Unattributed error - assign to first section as fallback
                        if section_names:
                            error_entry = f"FACTUAL ERROR in '{section_names[0]}': {line}"
                            errors.append(error_entry)

                return errors[:10]  # Limit total
        except Exception as e:
            logger.error(f"[Phase 1E] Batch fact-checking failed: {e}")

        return []

    def _finalize_review(self, review_notes: list):
        """Log and emit review results."""
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

    # ==================================================================
    # PHASE 1F: REVISE
    # ==================================================================

    def _phase1f_revise(self, state: DeepResearchState) -> dict:
        """Phase 1F: Apply final polishing and improvements."""
        document_path = state.get("document_path", "")
        notes_path = state.get("notes_path", "")
        review_notes = state.get("review_notes", [])

        logger.info(
            f"[Phase 1F] Applying final revisions and fact corrections"
        )
        logger.info(
            f"[Phase 1F] notes_path: '{notes_path}', {len(review_notes)} review notes"
        )
        self._emit_progress(
            "Phase 1F", "Correcting facts and polishing document"
        )

        # Load document
        doc_content = self._load_document_for_revision(document_path)
        if not doc_content:
            return self._revise_skip_state(state)

        # Apply all revisions (including intelligent section-level revisions)
        doc_content, revisions_applied = self._apply_all_revisions(
            doc_content, review_notes, notes_path, document_path
        )

        # Save revised document
        self._save_revised_document(
            document_path, doc_content, revisions_applied
        )

        self._emit_progress(
            "Phase 1F",
            f"Applied {len(revisions_applied)} improvements (including fact corrections)",
        )

        return {
            "messages": state.get("messages", []),
            "revisions_applied": revisions_applied,
            "current_phase": "finalize",
        }

    def _load_document_for_revision(self, document_path: str) -> str | None:
        """Load document content for revision."""
        if not document_path or not Path(document_path).exists():
            logger.error(f"[Phase 1F] Document not found: {document_path}")
            return None

        try:
            with open(document_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            logger.error(f"[Phase 1F] Failed to read document: {e}")
            return None

    def _revise_skip_state(self, state: DeepResearchState) -> dict:
        """Return state when skipping revision."""
        return {
            "messages": state.get("messages", []),
            "current_phase": "finalize",
        }

    def _apply_all_revisions(
        self,
        doc_content: str,
        review_notes: list,
        notes_path: str = "",
        document_path: str = None,
    ) -> tuple[str, list]:
        """Apply all revisions to document using intelligent section-level editing.

        Args:
            doc_content: Full document content
            review_notes: List of review issues
            notes_path: Path to research notes for RAG context
            document_path: Optional path to document file

        Returns:
            (revised_doc_content, list_of_revisions_applied)
        """
        revisions_applied = []

        # NEW: Intelligent section-level revisions with RAG context
        logger.info(
            f"[Phase 1F] Checking conditions - notes_path='{notes_path}' (len={len(notes_path) if notes_path else 0}), "
            f"review_notes count={len(review_notes)}"
        )

        if (
            notes_path
            and len(notes_path) > 0
            and review_notes
            and len(review_notes) > 0
        ):
            try:
                logger.info("[Phase 1F] Calling _apply_intelligent_revisions")
                doc_content, section_revisions = (
                    self._apply_intelligent_revisions(
                        doc_content, review_notes, notes_path, document_path
                    )
                )
                revisions_applied.extend(section_revisions)
                logger.info(
                    f"[Phase 1F] Intelligent revisions completed: {len(section_revisions)} revisions"
                )
            except Exception as e:
                logger.error(
                    f"[Phase 1F] Error in intelligent revisions: {e}",
                    exc_info=True,
                )
        else:
            logger.warning(
                f"[Phase 1F] Skipping intelligent revisions - "
                f"notes_path: {bool(notes_path)}, review_notes: {bool(review_notes)}"
            )

        # Apply formatting revisions
        doc_content, revisions = self._generate_abstract(doc_content)
        revisions_applied.extend(revisions)

        doc_content, revisions = self._generate_table_of_contents(doc_content)
        revisions_applied.extend(revisions)

        doc_content, revisions = self._deduplicate_sections(doc_content)
        revisions_applied.extend(revisions)

        # Ensure Sources section is present and populated
        # If it's missing or looks empty/broken, regenerate it from notes
        sources_match = re.search(
            r"## Sources.*?(?=\n##|\Z)", doc_content, re.DOTALL
        )
        sources_content = sources_match.group(0) if sources_match else ""

        if (
            not sources_match
            or len(sources_content) < 50
            or "No sources available" in sources_content
        ):
            if hasattr(self, "_synthesize_sources") and hasattr(
                self, "_parse_research_notes"
            ):
                if notes_path and Path(notes_path).exists():
                    try:
                        with open(notes_path, "r", encoding="utf-8") as f:
                            notes_content = f.read()
                        parsed_notes = self._parse_research_notes(
                            notes_content
                        )
                        sources_section = self._synthesize_sources(
                            parsed_notes
                        )

                        if sources_match:
                            # Replace existing bad section
                            doc_content = doc_content.replace(
                                sources_content, sources_section + "\n\n"
                            )
                            revisions_applied.append(
                                "Regenerated Sources section from notes"
                            )
                        else:
                            # Append
                            doc_content = (
                                doc_content.strip()
                                + "\n\n"
                                + sources_section
                                + "\n"
                            )
                            revisions_applied.append(
                                "Added Sources section from notes"
                            )

                        logger.info(
                            f"[Phase 1F] Regenerated Sources section with {len(sources_section)} chars"
                        )
                    except Exception as e:
                        logger.error(
                            f"[Phase 1F] Failed to regenerate sources: {e}"
                        )

        doc_content, revisions = self._normalize_section_spacing(doc_content)
        revisions_applied.extend(revisions)

        doc_content, revisions = self._add_source_count_to_title(doc_content)
        revisions_applied.extend(revisions)

        return doc_content, revisions_applied

    def _apply_intelligent_revisions(
        self,
        doc_content: str,
        review_notes: list,
        notes_path: str,
        document_path: str = None,
    ) -> tuple[str, list]:
        """Apply intelligent section-level revisions with RAG verification.

        This implements the user's requested workflow:
        1. Group review notes by section
        2. Load notes into RAG
        3. For each section with issues, query RAG and revise with context
        4. Apply section revisions to document

        Args:
            doc_content: Full document content
            review_notes: List of all review issues
            notes_path: Path to notes file for RAG context
            document_path: Optional path to document file

        Returns:
            (revised_doc_content, list_of_revisions_applied)
        """
        logger.info("[Phase 1F] Starting intelligent section-level revisions")
        revisions_applied = []

        # Step 1: Group review notes by section
        try:
            grouped_issues = self._group_review_notes_by_section(
                review_notes, doc_content
            )
            logger.info(
                f"[Phase 1F] Grouping complete - found {len(grouped_issues)} section groups"
            )
        except Exception as e:
            logger.error(
                f"[Phase 1F] Failed to group issues: {e}", exc_info=True
            )
            return doc_content, revisions_applied

        if not grouped_issues:
            logger.info("[Phase 1F] No section-specific issues to revise")
            return doc_content, revisions_applied

        # Check if there are any actionable section-specific issues
        actionable_sections = {
            k: v
            for k, v in grouped_issues.items()
            if k != "_general_" and len(v) > 0
        }
        if not actionable_sections:
            logger.info(
                "[Phase 1F] Only general issues found, skipping intelligent revisions"
            )
            return doc_content, revisions_applied

        logger.info(
            f"[Phase 1F] Grouped issues into {len(grouped_issues)} sections"
        )
        for section_name, section_issues in grouped_issues.items():
            logger.info(f"  - {section_name}: {len(section_issues)} issues")

        # Step 2: Handle temporal issues globally (apply to entire document)
        temporal_issues = [
            note
            for note in grouped_issues.get("_general_", [])
            if "temporal" in note.lower() and "issue" in note.lower()
        ]
        if temporal_issues:
            logger.info(
                f"[Phase 1F] Applying {len(temporal_issues)} temporal fixes globally"
            )
            doc_content = self._fix_temporal_references(doc_content)
            revisions_applied.append("Fixed temporal references globally")

        # Step 3: Ensure notes are loaded into RAG
        if self._api and hasattr(self._api, "ensure_indexed_files"):
            try:
                self._api.ensure_indexed_files([notes_path])
                logger.info(
                    "[Phase 1F] Loaded notes into RAG for verification"
                )
            except Exception as e:
                logger.warning(
                    f"[Phase 1F] Failed to load notes into RAG: {e}"
                )

        # Step 4: Revise each section with issues (limit to top 5 to avoid hangs)
        section_revisions = {}
        sections_to_revise = list(grouped_issues.items())[
            :5
        ]  # Limit to 5 sections max

        for section_name, issues in sections_to_revise:
            if section_name == "_general_":
                # Skip general issues for now (could be handled differently)
                logger.info(
                    f"[Phase 1F] Skipping {len(issues)} general issues"
                )
                continue

            logger.info(
                f"[Phase 1F] Processing section: {section_name} ({len(issues)} issues)"
            )

            # Extract current section content
            try:
                section_content = self._extract_section_content(
                    doc_content, section_name
                )
                if not section_content:
                    logger.warning(
                        f"[Phase 1F] Could not extract content for {section_name}"
                    )
                    continue
                logger.info(
                    f"[Phase 1F] Extracted {len(section_content)} chars from {section_name}"
                )
            except Exception as e:
                logger.error(
                    f"[Phase 1F] Failed to extract {section_name}: {e}",
                    exc_info=True,
                )
                continue

            # Revise section with RAG context
            try:
                revised_content = self._revise_section_with_context(
                    section_name, section_content, issues, notes_path
                )

                if revised_content:
                    section_revisions[section_name] = revised_content
                    logger.info(
                        f"[Phase 1F] Successfully revised {section_name}"
                    )
                else:
                    logger.warning(
                        f"[Phase 1F] Revision returned None for {section_name}"
                    )
            except Exception as e:
                logger.error(
                    f"[Phase 1F] Failed to revise {section_name}: {e}",
                    exc_info=True,
                )
                continue

        # Step 4: Apply all section revisions to document
        if section_revisions:
            logger.info(
                f"[Phase 1F] Applying {len(section_revisions)} section revisions to document"
            )
            try:
                doc_content, revisions = self._apply_section_revisions(
                    doc_content, section_revisions, document_path
                )
                revisions_applied.extend(revisions)
                logger.info(
                    f"[Phase 1F] Applied {len(revisions)} intelligent revisions"
                )
            except Exception as e:
                logger.error(
                    f"[Phase 1F] Failed to apply section revisions: {e}",
                    exc_info=True,
                )
        else:
            logger.warning("[Phase 1F] No section revisions to apply")

        # Step 5: Post-revision validation - check if original issues are fixed
        if revisions_applied and hasattr(self, "_validate_revisions"):
            remaining_issues = self._validate_revisions(
                doc_content, review_notes, notes_path
            )
            if remaining_issues:
                logger.warning(
                    f"[Phase 1F] Post-validation: {len(remaining_issues)} issues remain"
                )
                # Log what still needs fixing
                for issue in remaining_issues[:5]:  # Show first 5
                    logger.warning(f"  - Still present: {issue[:100]}...")
            else:
                logger.info("[Phase 1F] Post-validation: All issues resolved")

        return doc_content, revisions_applied

    def _check_writing_style(self, doc_content: str) -> list:
        """Check for redundant phrases, clichés, and academic filler.

        Args:
            doc_content: Full document content

        Returns:
            List of style issues found
        """
        issues = []

        # Common academic clichés and redundancies
        cliche_patterns = [
            (
                r"\bthe intersection of\b",
                "'the intersection of' (cliché - be more direct)",
            ),
            (
                r"\bpressing concern\b",
                "'pressing concern' (cliché - be more specific)",
            ),
            (
                r"\bmultifaceted and far-reaching\b",
                "'multifaceted and far-reaching' (redundant phrase)",
            ),
            (
                r"\bparadoxical approach\b.*?\bparadoxical",
                "'paradoxical' used multiple times",
            ),
            (
                r"\bthis research aims to analyze\b",
                "'this research aims to analyze' (wordy - use active voice)",
            ),
            (
                r"\bthe implications of this research\b",
                "'the implications of this research' (redundant - cut to findings)",
            ),
            (
                r"\bin recent years\b",
                "'in recent years' (vague - specify dates)",
            ),
            (
                r"\bcomplex and multifaceted\b",
                "'complex and multifaceted' (redundant)",
            ),
            (
                r"\bit is important to note\b",
                "'it is important to note' (filler - just state the point)",
            ),
            (
                r"\bhas become increasingly\b",
                "'has become increasingly' (weak - be specific)",
            ),
            (
                r"\bplay[s]? a.*?role in\b",
                "'play a role in' (weak verb - use stronger action)",
            ),
            (
                r"\bthe findings suggest that\b",
                "'the findings suggest that' (wordy - state finding directly)",
            ),
        ]

        import re

        for pattern, issue_desc in cliche_patterns:
            matches = list(re.finditer(pattern, doc_content, re.IGNORECASE))
            if matches:
                # Only report if it appears more than once OR is particularly egregious
                if len(matches) > 1:
                    issues.append(
                        f"STYLE: {issue_desc} (found {len(matches)} times)"
                    )
                elif "cliché" in issue_desc or "redundant" in issue_desc:
                    issues.append(f"STYLE: {issue_desc}")

        return issues

    def _extract_section_content(
        self, doc_content: str, section_name: str
    ) -> str | None:
        """Extract content of a specific section from document.

        Args:
            doc_content: Full document content
            section_name: Name of section to extract

        Returns:
            Section content (without header), or None if not found
        """
        import re

        # Pattern to match section header + content until next section or end
        pattern = rf"## {re.escape(section_name)}\n+(.*?)(?=\n##|\Z)"
        match = re.search(pattern, doc_content, re.DOTALL)

        if match:
            return match.group(1).strip()
        return None

    def _save_revised_document(
        self, document_path: str, doc_content: str, revisions_applied: list
    ):
        """Save revised document to file."""
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
            result = finalize_research_document(
                document_path=document_path, api=self
            )
            logger.info(f"[Finalize] {result}")
            self._emit_progress("Finalize", f"Document ready: {document_path}")

            # Unlock all research documents (main document, notes, and working draft)
            document_path_str = str(document_path)
            notes_path = state.get("notes_path", "")

            # Unlock main document
            if hasattr(self, "emit_signal"):
                from airunner.enums import SignalCode

                self.emit_signal(
                    SignalCode.UNLOCK_RESEARCH_DOCUMENT,
                    {"path": document_path_str},
                )
                logger.info(
                    f"[Finalize] Unlocked main document: {document_path_str}"
                )

                # Unlock notes if they exist
                if notes_path:
                    self.emit_signal(
                        SignalCode.UNLOCK_RESEARCH_DOCUMENT,
                        {"path": notes_path},
                    )
                    logger.info(f"[Finalize] Unlocked notes: {notes_path}")

        except Exception as e:
            logger.error(f"[Finalize] Failed to finalize: {e}")

        logger.info(f"✓ Research workflow completed for: {document_path}")

        return {
            "messages": state.get("messages", []),
            "current_phase": "complete",
        }
