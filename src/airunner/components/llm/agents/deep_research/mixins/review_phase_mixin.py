"""Review phase mixin for DeepResearchAgent.

Handles Phase 1E and 1F: reviewing document quality, applying corrections, and finalizing.
"""

import math
import os
import re
import logging
from collections import Counter
from pathlib import Path
from typing import TypedDict
from datetime import datetime

from langchain_core.messages import HumanMessage, SystemMessage

from airunner.components.llm.tools.research_document_tools import (
    finalize_research_document,
)

logger = logging.getLogger(__name__)

STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "that",
    "the",
    "this",
    "to",
    "with",
    "was",
    "were",
    "which",
    "will",
}


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

    def _get_review_system_prompt(self) -> str:
        """Return the base system prompt for review-side LLM tasks."""

        prompt = getattr(self, "_review_system_prompt", None)
        if prompt:
            return prompt

        return (
            "You are the Deep Research quality reviewer. Rely only on the artifacts supplied in the user "
            "message, flag concrete issues succinctly, and follow any format instructions provided."
        )

    def _build_review_messages(
        self, user_prompt: str, *, task_context: str = ""
    ) -> list:
        """Construct a [System, Human] message pair for review checks."""

        system_prompt = self._get_review_system_prompt()
        if task_context:
            system_prompt = (
                f"{system_prompt}\n\nTASK FOCUS:\n{task_context.strip()}"
            )

        return [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ]

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

        # Detect leaked instruction text or prompt artifacts
        review_notes.extend(self._check_instruction_artifacts(doc_content))

        # Analyze repetition and readability for each section
        review_notes.extend(self._analyze_word_repetition(doc_content))
        review_notes.extend(self._identify_global_repetitions(doc_content))
        review_notes.extend(self._detect_repeated_sentences(doc_content))
        review_notes.extend(self._detect_repetitive_starts(doc_content))
        review_notes.extend(self._evaluate_readability(doc_content))
        review_notes.extend(self._detect_section_overlap(doc_content))
        review_notes.extend(self._detect_duplicate_headers(doc_content))
        review_notes.extend(self._detect_thin_sections(doc_content))

        # Verify named officials/titles against notes to prevent hallucinated roles
        review_notes.extend(
            self._check_titles_against_notes(doc_content, notes_path)
        )

        # Check for potential bias or loaded language
        review_notes.extend(self._detect_bias(doc_content))

        return review_notes

    def _detect_bias(self, doc_content: str) -> list:
        """Detect potential bias, loaded language, or subjective intensifiers."""

        issues = []

        # 1. Subjective Intensifiers (words that claim truth without proof)
        intensifiers = [
            "clearly",
            "obviously",
            "undoubtedly",
            "undeniably",
            "unquestionably",
            "absolutely",
            "certainly",
            "definitely",
            "without a doubt",
        ]

        # 2. Loaded/Emotional Language (words that imply judgment)
        loaded_words = [
            "disastrous",
            "catastrophic",
            "miraculous",
            "incredible",
            "shocking",
            "shameful",
            "disgraceful",
            "appalling",
            "horrific",
            "wonderful",
            "fantastic",
            "amazing",
            "terrible",
            "awful",
            "radical",
            "extremist",
            "fanatical",
            "corrupt",
            "crooked",
            "incompetent",
        ]

        # 3. Generalizations
        generalizations = [
            "everyone knows",
            "no one believes",
            "always",
            "never",
            "all people",
            "every citizen",
        ]

        # Check for these patterns
        for word in intensifiers:
            if re.search(
                r"\b" + re.escape(word) + r"\b", doc_content, re.IGNORECASE
            ):
                issues.append(
                    f"BIAS CHECK: Found subjective intensifier '{word}'. Ensure this is supported by facts or attribute it to a source."
                )

        for word in loaded_words:
            if re.search(
                r"\b" + re.escape(word) + r"\b", doc_content, re.IGNORECASE
            ):
                issues.append(
                    f"BIAS CHECK: Found loaded language '{word}'. Use neutral, descriptive terms instead."
                )

        for phrase in generalizations:
            if re.search(
                r"\b" + re.escape(phrase) + r"\b", doc_content, re.IGNORECASE
            ):
                issues.append(
                    f"BIAS CHECK: Found generalization '{phrase}'. Be specific about who holds this view."
                )

        return issues

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
        """Check for inappropriate temporal references without hardcoding job titles.

        CRITICAL: Research documents should use timeless language. When describing actions
        that occurred while someone held a specific office, refer to that role directly unless
        the contrast between time periods is the point of the sentence.
        """
        review_notes = []

        # Common temporal issues
        temporal_patterns = [
            (
                r"\bformer\s+(?:[A-Z][a-z]+|[A-Z]{2,})(?:\s+(?:[A-Z][a-z]+|[A-Z]{2,}))*",
                "Avoid 'former' qualifiers unless contrasting time periods explicitly",
                0,
            ),
            (
                r"\bformer\s+[a-z]+(?:\s+[a-z]+){0,2}(?=\s+[A-Z])",
                "Remove 'former' before titles when the surrounding context already establishes timing",
                re.IGNORECASE,
            ),
            (
                r"\bcurrently\b|\bat present\b|\bright now\b|\bthese days\b",
                "Avoid temporal markers—describe facts relative to the events instead",
                re.IGNORECASE,
            ),
            (
                r"\brecently\s+(?:announced|released|introduced|completed)|has\s+just",
                "Use concrete timing instead of 'recently/just' phrasing",
                re.IGNORECASE,
            ),
        ]

        for pattern, issue, flags in temporal_patterns:
            matches = re.findall(pattern, doc_content, flags)
            if matches:
                review_notes.append(
                    f"TEMPORAL ISSUE: {issue} (found {len(matches)} instance(s))"
                )
                logger.warning(
                    f"[Phase 1E] Temporal reference issue: {matches[0]} - {issue}"
                )

        return review_notes

    def _fix_temporal_references(self, doc_content: str) -> str:
        """Apply global fixes for temporal reference issues without naming specific roles."""

        def _strip_former(match: re.Match) -> str:
            # Keep the title text but drop the "former" qualifier
            return match.group(1)

        title_pattern = re.compile(
            r"\bformer\s+((?:[A-Z][a-z]+|[A-Z]{2,})(?:\s+(?:[A-Z][a-z]+|[A-Z]{2,}))*)(?=\s+[A-Z])"
        )
        doc_content = title_pattern.sub(_strip_former, doc_content)

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

    def _check_instruction_artifacts(self, doc_content: str) -> list:
        """Detect stray instruction text that should never appear in final prose."""

        issues = []
        instruction_patterns = [
            r"Use the present tense when",
            r"Use the past tense when",
            r"Use the future tense when",
            r"Use the present perfect tense",
            r"Use the past perfect tense",
            r"Use the present continuous tense",
            r"Use the past continuous tense",
            r"Use the subjunctive",
            r"DISAMBIGUATE",
            r"CRITICAL:\s+DISAMBIGUATE",
            r"Please revise the given text",
            r"Please revise the text",
            r"Here is the requested section",
            r"next section",
            r"timeline is unclear",
            r"avoid making claims that",
            r"paraphrased statement should be supported",
            r"reference the evidence;",
            r"cite the evidence rather than",
        ]

        for pattern in instruction_patterns:
            match = re.search(pattern, doc_content, re.IGNORECASE)
            if match:
                snippet = doc_content[match.start() : match.start() + 120]
                issues.append(
                    f"INSTRUCTION ARTIFACT: Found prompt text leaking into prose ('{snippet.strip()}')."
                )

        # Detect bullet blocks of instructions (2 or more consecutive '- Use ...' lines)
        bullet_pattern = re.compile(
            r"(?:^|\n)(?:[A-Z][^\n]*?:)?\s*(?:-\s*(?:Use|Ensure|Avoid|Do not|Keep|Maintain)[^\n]*\n){2,}",
            re.IGNORECASE,
        )
        for match in bullet_pattern.finditer(doc_content):
            snippet = (
                doc_content[match.start() : match.end()]
                .strip()
                .split("\n")[:3]
            )
            issues.append(
                f"INSTRUCTION ARTIFACT: Remove instructional bullet list starting with '{' '.join(snippet)}'."
            )

        return issues

    def _detect_section_overlap(self, doc_content: str) -> list:
        """Detect sections that substantially duplicate one another."""

        issues = []
        section_pattern = re.compile(r"## (.+?)\n(.*?)(?=\n##|\Z)", re.DOTALL)
        parsed_sections = []

        for match in section_pattern.finditer(doc_content):
            section_name = match.group(1).strip()
            section_text = match.group(2)
            tokens = re.findall(r"[A-Za-z']+", section_text.lower())
            filtered = [
                tok for tok in tokens if tok not in STOPWORDS and len(tok) > 3
            ]

            if len(filtered) < 120:
                continue

            vector = Counter(filtered)
            norm = math.sqrt(sum(count * count for count in vector.values()))
            if norm == 0:
                continue

            parsed_sections.append(
                {
                    "name": section_name,
                    "vector": vector,
                    "norm": norm,
                }
            )

        for idx, current in enumerate(parsed_sections):
            for other in parsed_sections[idx + 1 :]:
                dot = sum(
                    current["vector"].get(word, 0)
                    * other["vector"].get(word, 0)
                    for word in current["vector"]
                )
                similarity = dot / (current["norm"] * other["norm"])

                if similarity >= 0.78:
                    issues.append(
                        "STRUCTURE ISSUE: Sections "
                        f"'{current['name']}' and '{other['name']}' overlap heavily "
                        f"(similarity {similarity:.0%}). Merge them or assign distinct angles."
                    )

        return issues

    def _detect_duplicate_headers(self, doc_content: str) -> list:
        """Flag repeated headers such as '## Title' followed by a setext version."""

        issues = []
        pattern = re.compile(
            r"(##\s+([^\n]+))\n+(?:\s*\n)*\s*\2\s*\n[=-]{3,}",
            re.IGNORECASE,
        )

        for match in pattern.finditer(doc_content):
            header_text = match.group(2).strip()
            issues.append(
                f"STRUCTURE ISSUE: Section '{header_text}' includes duplicate headers (H2 plus underlined repeat). Remove the redundant title before finalizing."
            )

        return issues

    def _detect_thin_sections(self, doc_content: str) -> list:
        """Warn when a section contains only a sentence or two."""

        issues = []
        section_pattern = re.compile(r"## (.+?)\n(.*?)(?=\n##|\Z)", re.DOTALL)

        for match in section_pattern.finditer(doc_content):
            section_name = match.group(1).strip()
            section_text = match.group(2).strip()
            word_count = len(section_text.split())
            if word_count and word_count < 80:
                issues.append(
                    f"CONTENT GAP: '{section_name}' is only {word_count} words. Expand it with evidence-backed analysis or merge it with an adjacent section."
                )

        return issues

    def _analyze_word_repetition(self, doc_content: str) -> list:
        """Identify sections where a single word dominates, suggesting repetitive prose."""

        issues = []
        section_pattern = re.compile(r"## (.+?)\n(.*?)(?=\n##|\Z)", re.DOTALL)

        for match in section_pattern.finditer(doc_content):
            section_name = match.group(1).strip()
            section_text = match.group(2)
            words = re.findall(r"[A-Za-z']+", section_text.lower())
            filtered = [w for w in words if w not in STOPWORDS and len(w) > 3]

            if len(filtered) < 60:  # skip short sections
                continue

            freq = Counter(filtered)
            top_word, count = freq.most_common(1)[0]
            ratio = count / len(filtered)

            if count >= 6 and ratio >= 0.06:
                issues.append(
                    f"WRITING QUALITY: '{section_name}' repeats '{top_word}' {count} times ({ratio:.0%} of meaningful words). Consider varying language."
                )

        return issues

    def _identify_global_repetitions(self, doc_content: str) -> list:
        """Surface words that dominate the entire document."""

        words = re.findall(r"[A-Za-z']+", doc_content.lower())
        filtered = [w for w in words if w not in STOPWORDS and len(w) > 3]
        if not filtered:
            return []

        freq = Counter(filtered)
        issues = []
        # Increased to top 10 to catch more issues
        for word, count in freq.most_common(10):
            # Lowered threshold to 6 for very frequent words in short docs,
            # but let's keep 8 as a safe baseline for now, maybe scale with doc length?
            # If doc is long, 8 is fine. If short, 8 is a lot.
            # Let's stick to 8 but make the message stronger.
            if count < 8:
                break
            issues.append(
                f"WORD CHOICE: '{word}' appears {count} times overall. This is excessive. Use synonyms or restructure sentences to avoid this word."
            )

        return issues

    def _detect_repetitive_starts(self, doc_content: str) -> list:
        """Flag paragraphs that start with the same phrase."""

        issues = []
        # Split into paragraphs
        paragraphs = [
            p.strip() for p in doc_content.split("\n\n") if len(p.strip()) > 50
        ]

        starts = []
        for p in paragraphs:
            # Get first 4 words
            words = p.split()[:4]
            if len(words) >= 3:
                starts.append(" ".join(words).lower())

        start_freq = Counter(starts)
        for phrase, count in start_freq.items():
            if count >= 2:
                issues.append(
                    f"REPETITIVE PHRASING: {count} paragraphs start with '{phrase}...'. Vary your sentence structures."
                )

        return issues

    def _detect_repeated_sentences(self, doc_content: str) -> list:
        """Flag sentences that appear verbatim multiple times in the paper."""

        sentences = re.split(r"(?<=[.!?])\s+", doc_content)
        normalized = []
        for sentence in sentences:
            clean = sentence.strip()
            if not clean or "##" in clean or len(clean) < 40:
                continue
            normalized.append(clean)

        freq = Counter(normalized)
        issues = []
        for sentence, count in freq.most_common():
            if count < 2:
                break
            preview = sentence[:160] + ("..." if len(sentence) > 160 else "")
            issues.append(
                f"STRUCTURE ISSUE: The sentence '{preview}' appears {count} times. Merge or rewrite to keep each section distinct."
            )
            if len(issues) >= 5:
                break

        return issues

    def _detect_repetitive_starts(self, doc_content: str) -> list:
        """Detect sections or sentences that repetitively start with the same few words."""

        issues = []
        section_pattern = re.compile(r"## (.+?)\n(.*?)(?=\n##|\Z)", re.DOTALL)

        for match in section_pattern.finditer(doc_content):
            section_name = match.group(1).strip()
            section_text = match.group(2)
            sentences = re.split(r"(?<=[.!?])\s+", section_text)
            normalized = []
            for sentence in sentences:
                clean = sentence.strip()
                if not clean or "##" in clean or len(clean) < 40:
                    continue
                normalized.append(clean)

            if len(normalized) < 3:
                continue

            # Check first few words of each sentence
            start_words = [s[:30] for s in normalized]
            freq = Counter(start_words)
            for words, count in freq.most_common():
                if count > 1:
                    issues.append(
                        f"STRUCTURE ISSUE: Section '{section_name}' repetitively starts with the same words: '{words.strip()}'. Vary the openings to enhance engagement."
                    )

        return issues

    def _evaluate_readability(self, doc_content: str) -> list:
        """Compute readability heuristics to flag dense or overly complex sections."""

        issues = []
        section_pattern = re.compile(r"## (.+?)\n(.*?)(?=\n##|\Z)", re.DOTALL)

        for match in section_pattern.finditer(doc_content):
            section_name = match.group(1).strip()
            section_text = match.group(2).strip()
            if len(section_text.split()) < 120:  # skip short blocks
                continue

            score = self._calculate_flesch_reading_ease(section_text)
            if score is None:
                continue

            if score < 20:
                issues.append(
                    f"WRITING QUALITY: '{section_name}' readability score {score:.1f} (very dense). Consider simplifying sentences."
                )
            elif score > 80:
                issues.append(
                    f"WRITING QUALITY: '{section_name}' readability score {score:.1f} (overly simple for research tone). Consider enriching detail."
                )

        return issues

    def _calculate_flesch_reading_ease(self, text: str) -> float | None:
        """Compute Flesch Reading Ease using lightweight heuristics."""

        sentences = re.split(r"[.!?]+", text)
        sentences = [s.strip() for s in sentences if s.strip()]
        if not sentences:
            return None

        words = re.findall(r"[A-Za-z']+", text)
        if not words:
            return None

        syllables = sum(self._estimate_syllables(w) for w in words)

        sentence_count = max(len(sentences), 1)
        word_count = max(len(words), 1)
        syllable_count = max(syllables, 1)

        asl = word_count / sentence_count
        asw = syllable_count / word_count

        return 206.835 - (1.015 * asl) - (84.6 * asw)

    @staticmethod
    def _estimate_syllables(word: str) -> int:
        """Very rough syllable estimate for readability metrics."""

        word = word.lower()
        if len(word) <= 3:
            return 1

        vowels = "aeiouy"
        syllables = 0
        prev_char_was_vowel = False

        for char in word:
            is_vowel = char in vowels
            if is_vowel and not prev_char_was_vowel:
                syllables += 1
            prev_char_was_vowel = is_vowel

        if word.endswith("e") and syllables > 1:
            syllables -= 1

        if syllables == 0:
            syllables = 1

        return syllables

    def _check_titles_against_notes(
        self, doc_content: str, notes_path: str
    ) -> list:
        """Ensure people+title pairs in the document exist within the research notes."""

        if not notes_path or not os.path.exists(notes_path):
            return []

        try:
            notes_content = Path(notes_path).read_text(encoding="utf-8")
        except Exception as exc:
            logger.warning(
                f"[Phase 1E] Could not read notes for title verification: {exc}"
            )
            return []

        doc_excerpt = doc_content[:8000]
        notes_excerpt = notes_content[:8000]

        task_context = (
            "Verify that every person referenced with a formal title in the document is supported by the research "
            "notes. Use ONLY the notes as ground truth, flag mismatches as 'ROLE ISSUE: <detail>', and if everything "
            "is supported respond with 'No unsupported titles found.'"
        )
        user_prompt = (
            "RESEARCH NOTES (truncated to 8000 chars):\n"
            f"{notes_excerpt}\n\n"
            "DOCUMENT EXCERPT (first 8000 chars):\n"
            f"{doc_excerpt}\n\nIdentify unsupported or conflicting title assignments:"
        )

        try:
            response = self._base_model.invoke(
                self._build_review_messages(
                    user_prompt, task_context=task_context
                ),
                temperature=0.1,
                max_new_tokens=512,
            )
        except Exception as exc:
            logger.error(
                f"[Phase 1E] Failed to run title verification check: {exc}"
            )
            return []

        if not getattr(response, "content", "").strip():
            return []

        result = response.content.strip()
        if "no unsupported" in result.lower():
            return []

        issues = []
        for line in result.split("\n"):
            clean_line = line.strip().lstrip("- ")
            if not clean_line:
                continue
            issues.append(f"ROLE ISSUE: {clean_line}")

        if issues:
            logger.warning(
                f"[Phase 1E] Title verification found {len(issues)} potential issue(s)"
            )

        return issues[:8]

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

        today = datetime.now().strftime("%B %d, %Y")
        task_rules = (
            "Review each provided section for factual errors. When you find an issue write 'SECTION [number]: <issue>'. "
            "Skip clean sections, and if every section is correct respond exactly with 'No factual errors detected.'"
        )
        user_prompt = (
            f"THESIS: {thesis}\n"
            f"TODAY'S DATE: {today}\n\n"
            "SECTIONS TO CHECK:\n"
            f"{sections_text}\n\nProvide the fact-check findings now."
        )

        try:
            messages_builder = getattr(
                self, "_build_fact_check_messages", None
            )
            if not messages_builder:
                raise AttributeError(
                    "ReviewPhaseMixin requires _build_fact_check_messages to dispatch fact-checking prompts"
                )

            response = self._base_model.invoke(
                messages_builder(user_prompt, extra_system_rules=task_rules),
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
