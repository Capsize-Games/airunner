"""Visible-response recovery helpers for node functions."""

import re
from typing import Optional

from langchain_core.messages import AIMessage

from airunner.components.llm.utils.thinking_parser import strip_thinking_tags


class ResponseRecoveryMixin:
    """Recover user-facing text from reasoning-heavy internal responses."""

    @staticmethod
    def _extract_committed_answer_text_field(text: str) -> str:
        """Extract one line-bounded answer_text block from stage output."""
        content = str(text or "")
        if not content.strip():
            return ""

        block_pattern = re.compile(
            r"(?:^|\n)\s*<answer_text>\s*(.*?)\s*</answer_text>\s*(?=\n|$)",
            flags=re.IGNORECASE | re.DOTALL,
        )
        match = block_pattern.search(content)
        if match:
            return match.group(1).strip()

        labelled_match = re.search(
            r"^answer_text\s*:\s*(.+)\Z",
            str(text or "").strip(),
            flags=re.IGNORECASE | re.DOTALL,
        )
        if labelled_match:
            return labelled_match.group(1).strip()

        return ""

    @staticmethod
    def _looks_like_answer_text_placeholder(text: str) -> bool:
        """Return True when answer_text content is still a schema placeholder."""
        normalized = " ".join(str(text or "").strip().lower().split())
        if not normalized:
            return False

        normalized = normalized.strip("[](){}<>'\"` ")
        return normalized in {
            "final user-facing answer",
            "write the completed final answer here",
            "your completed final answer here",
            "completed final answer here",
            "actual final answer here",
            "insert final answer here",
            "replace with the completed final answer",
            "...",
        }

    def _extract_committed_response_content(
        self,
        response_message: Optional[AIMessage],
        *,
        reject_structure_only: bool = False,
    ) -> str:
        """Return one exact committed answer_text field from stage output."""
        if response_message is None:
            return ""

        visible_content = str(getattr(response_message, "content", "") or "")
        if visible_content.strip():
            structured_visible = self._sanitize_recovered_response_candidate(
                self._extract_committed_answer_text_field(visible_content),
                reject_structure_only=reject_structure_only,
            )
            if structured_visible:
                return structured_visible

        additional_kwargs = (
            getattr(response_message, "additional_kwargs", {}) or {}
        )
        thinking_content = (
            additional_kwargs.get("thinking_content")
            or additional_kwargs.get("reasoning_content")
            or ""
        )
        cleaned_thinking = strip_thinking_tags(str(thinking_content)).strip()
        if not cleaned_thinking:
            return ""

        return self._sanitize_recovered_response_candidate(
            self._extract_committed_answer_text_field(cleaned_thinking),
            reject_structure_only=reject_structure_only,
        )

    @staticmethod
    def _extract_answer_text_field(text: str) -> str:
        """Extract one structured answer-text field when present."""
        content = str(text or "").strip()
        if not content:
            return ""

        tagged_match = re.search(
            r"<answer_text>\s*(.*?)\s*</answer_text>",
            content,
            flags=re.IGNORECASE | re.DOTALL,
        )
        if tagged_match:
            return tagged_match.group(1).strip()

        labelled_match = re.search(
            r"^answer_text\s*:\s*(.+)\Z",
            content,
            flags=re.IGNORECASE | re.DOTALL,
        )
        if labelled_match:
            return labelled_match.group(1).strip()

        return ""

    def _sanitize_recovered_response_candidate(
        self,
        text: str,
        *,
        reject_structure_only: bool = False,
    ) -> str:
        """Return one user-facing candidate or an empty string."""
        candidate = self._clean_reasoning_candidate(text)
        if not candidate:
            return ""
        if self._looks_like_answer_text_placeholder(candidate):
            return ""
        if self._looks_like_malformed_forced_response_fragment(candidate):
            return ""
        if reject_structure_only and self._looks_like_summary_scaffolding_response(
            candidate
        ):
            return ""
        return candidate

    def _recover_forced_response_content(
        self,
        response_message: Optional[AIMessage],
        *,
        reject_structure_only: bool = False,
    ) -> str:
        """Recover a visible answer from a reasoning-only internal pass."""
        if response_message is None:
            return ""

        rejected_visible = ""
        visible_content = str(getattr(response_message, "content", "") or "")
        if visible_content.strip():
            structured_visible = self._sanitize_recovered_response_candidate(
                self._extract_answer_text_field(visible_content),
                reject_structure_only=reject_structure_only,
            )
            if structured_visible:
                return structured_visible
            cleaned_visible = self._strip_forced_response_label(visible_content)
            visible_candidate = self._sanitize_recovered_response_candidate(
                cleaned_visible,
                reject_structure_only=reject_structure_only,
            )
            if visible_candidate:
                return visible_candidate
            rejected_visible = cleaned_visible

        additional_kwargs = getattr(response_message, "additional_kwargs", {}) or {}
        thinking_content = (
            additional_kwargs.get("thinking_content")
            or additional_kwargs.get("reasoning_content")
            or ""
        )
        cleaned_thinking = strip_thinking_tags(str(thinking_content)).strip()
        if not cleaned_thinking:
            return ""

        structured_thinking = self._sanitize_recovered_response_candidate(
            self._extract_answer_text_field(cleaned_thinking),
            reject_structure_only=reject_structure_only,
        )
        if structured_thinking:
            self.logger.info(
                "Recovered structured answer_text from reasoning output"
            )
            return structured_thinking

        drafted_response = self._sanitize_recovered_response_candidate(
            self._extract_drafted_response_from_thinking(cleaned_thinking),
            reject_structure_only=reject_structure_only,
        )
        if drafted_response:
            self.logger.info(
                "Recovered drafted forced response from reasoning-only output"
            )
            return drafted_response

        if reject_structure_only:
            normalized_reasoning_summary = self._normalize_numbered_summary_response(
                cleaned_thinking
            )
            if normalized_reasoning_summary:
                self.logger.info(
                    "Recovered summary prose from numbered reasoning output"
                )
                return normalized_reasoning_summary

        paragraphs = [
            paragraph.strip()
            for paragraph in re.split(r"\n\s*\n", cleaned_thinking)
            if paragraph.strip()
        ]
        for paragraph in paragraphs:
            candidate = self._sanitize_recovered_response_candidate(
                paragraph,
                reject_structure_only=reject_structure_only,
            )
            if candidate:
                self.logger.info(
                    "Recovered visible forced response from reasoning-only output"
                )
                return candidate

        if reject_structure_only and rejected_visible:
            normalized_inventory = self._normalize_inventory_summary_response(
                rejected_visible
            )
            if normalized_inventory:
                self.logger.info(
                    "Flattened list-style summary into visible prose"
                )
                return normalized_inventory

        return ""

    def _extract_drafted_response_from_thinking(
        self,
        cleaned_thinking: str,
    ) -> str:
        """Extract quoted draft sentences from structured reasoning output."""
        section_headings = [
            "Final Polish",
            "Refine the Response",
            "Refining for Conciseness and Flow",
            "Draft the Response",
            "Drafting the Response",
        ]
        for heading in section_headings:
            section = self._extract_reasoning_section(cleaned_thinking, heading)
            if not section:
                continue

            preferred_quote = self._extract_preferred_quote_from_section(section)
            if preferred_quote:
                return preferred_quote

            quotes = self._extract_quoted_response_lines(section)
            if quotes:
                return " ".join(quotes)

            draft_line = self._extract_labelled_draft_line(section)
            if draft_line:
                return draft_line

        labelled_response = self._extract_labelled_reasoning_response(
            cleaned_thinking
        )
        if labelled_response:
            return labelled_response

        numbered_draft = self._extract_numbered_draft_sentences(cleaned_thinking)
        if numbered_draft:
            return numbered_draft

        return ""

    def _extract_numbered_draft_sentences(
        self,
        cleaned_thinking: str,
    ) -> str:
        """Extract one numbered draft sentence block from reasoning text."""
        capture = False
        current_item = ""
        sentences: list[str] = []

        def flush_current() -> None:
            nonlocal current_item
            candidate = self._clean_reasoning_candidate(current_item)
            if candidate:
                sentences.append(candidate)
            current_item = ""

        for raw_line in cleaned_thinking.splitlines():
            stripped = raw_line.strip()
            lowered = stripped.lower()
            if not capture:
                if "drafting sentences" in lowered:
                    capture = True
                continue

            if current_item and re.match(r"^\d+\.\s+", stripped):
                flush_current()
            if "review against constraints" in lowered:
                break
            match = re.match(r"^\d+\.\s+(.+)$", stripped)
            if match:
                current_item = match.group(1).strip()
                continue
            if current_item and raw_line[:1].isspace() and stripped:
                current_item = f"{current_item} {stripped}"
                continue
            if current_item and not stripped:
                flush_current()

        if current_item:
            flush_current()
        return " ".join(sentences)

    def _extract_labelled_reasoning_response(
        self,
        cleaned_thinking: str,
    ) -> str:
        """Extract one substantive answer from free-form labelled reasoning."""
        labelled_candidates: list[tuple[int, str]] = []

        for raw_line in cleaned_thinking.splitlines():
            parsed = self._parse_reasoning_labelled_line(raw_line)
            if not parsed:
                continue
            label, body = parsed
            candidate = self._clean_reasoning_candidate(body)
            if not candidate or self._looks_like_malformed_forced_response_fragment(
                candidate
            ):
                continue

            lowered_label = " ".join(label.lower().split())
            score = 0
            if lowered_label in {
                "final answer",
                "final polish",
                "final response",
            }:
                score = 5
            elif lowered_label == "substantive content":
                score = 4
            elif lowered_label in {"summary", "answer", "response"}:
                score = 3
            elif lowered_label in {"draft", "draft answer", "draft response"}:
                score = 2
            elif lowered_label == "content":
                score = 1

            if score:
                labelled_candidates.append((score, candidate))

        if not labelled_candidates:
            return ""

        labelled_candidates.sort(
            key=lambda item: (item[0], len(item[1])),
            reverse=True,
        )
        return labelled_candidates[0][1]

    @staticmethod
    def _parse_reasoning_labelled_line(line: str) -> tuple[str, str] | None:
        """Return one `(label, body)` pair from a labelled reasoning line."""
        candidate = line.strip()
        if not candidate:
            return None

        candidate = re.sub(r"^(?:[-*+]\s+)", "", candidate).strip()
        patterns = (
            r'^\*\*([^*]+):\*\*\s*(.+)$',
            r'^\*([^*]+):\*\s*(.+)$',
            r'^\*([^*]+)\*:\s*(.+)$',
            r'^"([^"]+):"\s*(.+)$',
            r'^([^:]{3,80}):\s*(.+)$',
        )
        for pattern in patterns:
            match = re.match(pattern, candidate)
            if not match:
                continue

            label = match.group(1).strip()
            body = match.group(2).strip()
            body_text = re.sub(r"[^A-Za-z0-9]+", "", body)
            if not body_text:
                continue
            lowered_label = label.lower()
            if any(
                marker in lowered_label
                for marker in (
                    "constraint",
                    "refining",
                    "instruction",
                    "self-correction",
                    "review",
                    "check",
                    "prompt says",
                    "do not repeat",
                )
            ):
                return None
            return label, body

        return None

    def _extract_preferred_quote_from_section(self, section: str) -> str:
        """Return one preferred quoted answer from a reasoning section."""
        labelled_quotes: list[tuple[str, str]] = []
        pattern = re.compile(
            r'^\s*\*\s+(?:\*([^*]+):\*\s*)?"(.+?)"\s*$',
            flags=re.MULTILINE,
        )
        for match in pattern.finditer(section):
            label = (match.group(1) or "").strip().lower()
            quote = match.group(2).strip()
            if quote:
                labelled_quotes.append((label, quote))

        if not labelled_quotes:
            return ""

        preferred_labels = {
            "combine for flow",
            "final answer",
            "final polish",
            "draft",
        }
        for label, quote in reversed(labelled_quotes):
            if label in preferred_labels:
                return quote

        if len(labelled_quotes) == 1:
            return labelled_quotes[0][1]
        return ""

    def _extract_quoted_response_lines(self, section: str) -> list[str]:
        """Return quoted response lines from one reasoning section."""
        return [
            match.group(1).strip()
            for match in re.finditer(
                r'^\s*\*\s+(?:\*[^*]+:\*\s*)?"(.+?)"\s*$',
                section,
                flags=re.MULTILINE,
            )
            if match.group(1).strip()
        ]

    def _extract_labelled_draft_line(self, section: str) -> str:
        """Return one unquoted draft line from a reasoning section."""
        patterns = [r'^\s*\*Draft:\*\s*(.+)$', r'^\s*Draft:\s*(.+)$']
        for pattern in patterns:
            match = re.search(pattern, section, flags=re.MULTILINE)
            if not match:
                continue
            candidate = self._clean_reasoning_candidate(match.group(1))
            if candidate:
                return candidate
        return ""

    def _extract_reasoning_section(
        self,
        cleaned_thinking: str,
        heading: str,
    ) -> str:
        """Return one numbered reasoning section by heading label."""
        pattern = re.compile(
            rf"\d+\.\s+\*\*{re.escape(heading)}:\*\*(?:[^\n]*)\n(.*?)(?=\n\d+\.\s+\*\*|\Z)",
            flags=re.DOTALL,
        )
        match = pattern.search(cleaned_thinking)
        if not match:
            return ""
        return match.group(1).strip()