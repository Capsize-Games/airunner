"""Response classification and normalization helpers for node functions."""

import re


class ResponseClassifierMixin:
    """Provide classifier helpers for visible-response recovery."""

    @staticmethod
    def _strip_forced_response_label(text: str) -> str:
        """Remove one synthetic response label from visible text."""
        cleaned = str(text or "").strip()
        if not cleaned:
            return ""

        patterns = (
            r"^(?:\*\*)?draft(?:\*\*)?\s*:\s*(.+)$",
            r"^(?:\*\*)?answer(?:\*\*)?\s*:\s*(.+)$",
            r"^(?:\*\*)?response(?:\*\*)?\s*:\s*(.+)$",
            r"^(?:\*\*)?final answer(?:\*\*)?\s*:\s*(.+)$",
            r"^(?:\*\*)?final response(?:\*\*)?\s*:\s*(.+)$",
        )
        for pattern in patterns:
            match = re.match(
                pattern,
                cleaned,
                flags=re.IGNORECASE | re.DOTALL,
            )
            if match:
                return match.group(1).strip()

        return cleaned

    @staticmethod
    def _looks_like_instruction_reflection(text: str) -> bool:
        """Return True for meta self-corrections, not user-facing answers."""
        lowered = " ".join(str(text or "").lower().split())
        if not lowered:
            return False
        markers = (
            "actually, rereading",
            "rereading:",
            "looking at the instruction",
            "looking at the instructions",
            "do not mention search results or instructions",
            "i should ensure",
            "i should just",
            "strict adherence",
            "this is a specific constraint",
            "respond naturally implies",
            "let's aim for",
            "don't add fluff",
            "just state the facts",
            "this looks like an instruction or a note rather than a full answer",
            "treat it as the starting point",
            "to be verified against search results",
        )
        if any(marker in lowered for marker in markers):
            return True
        return (
            "search results" in lowered
            and any(
                marker in lowered
                for marker in ("verify", "verified", "instruction")
            )
        )

    @staticmethod
    def _looks_like_summary_prompt_echo(text: str) -> bool:
        """Return True when visible text is just summary guidance echoed back."""
        lowered = " ".join(str(text or "").lower().split())
        if not lowered:
            return False

        markers = (
            "explain the central worldview",
            "explain the central argument",
            "explain the central subject",
            "cover supporting ideas",
            "cover the most important supporting ideas",
            "merge overlapping evidence",
            "prefer specific details",
            "keep isolated front-matter anecdotes",
            "stay anchored to what the excerpts explicitly say",
        )
        return sum(marker in lowered for marker in markers) >= 2

    @staticmethod
    def _looks_like_search_result_preface_response(text: str) -> bool:
        """Return True for search-engine style summaries and offers."""
        lowered = " ".join(str(text or "").lower().split())
        if not lowered:
            return False
        if lowered.startswith("based on the search results"):
            return True
        if lowered.startswith("from the search results"):
            return True
        if lowered.startswith("based on the document excerpt"):
            return True
        if lowered.startswith("from the document excerpt"):
            return True
        if "appears to be" in lowered and "would you like me to search" in lowered:
            return True
        return any(
            marker in lowered
            for marker in (
                "would you like me to search",
                "i can help you find more information",
                "i can help you find more details",
            )
        )

    @staticmethod
    def _looks_like_summary_direction_response(text: str) -> bool:
        """Return True for imperative summary directions, not answers."""
        lowered = " ".join(str(text or "").lower().split())
        if not lowered:
            return False

        directive_prefixes = (
            "focus on ",
            "focus the summary on ",
            "emphasize ",
            "highlight ",
            "prioritize ",
            "stick to ",
            "lead with ",
        )
        if not lowered.startswith(directive_prefixes):
            return False

        word_count = len(lowered.split())
        if word_count <= 24 and (
            lowered.count(",") >= 2
            or any(
                marker in lowered
                for marker in (
                    " and the ",
                    " and her ",
                    " and his ",
                    " and their ",
                    " and its ",
                )
            )
        ):
            return True

        directive_markers = (
            "aspect",
            "aspects",
            "character",
            "characters",
            "clue",
            "clues",
            "conversation",
            "detail",
            "details",
            "murder mystery",
            "premise",
            "setting",
            "snapshot",
            "theme",
        )
        return any(marker in lowered for marker in directive_markers)

    @staticmethod
    def _looks_like_document_summary_clarification_response(text: str) -> bool:
        """Return True for clarification requests replacing a summary."""
        lowered = " ".join(str(text or "").lower().split())
        if not lowered:
            return False

        markers = (
            "which specific book you're referring to",
            "which specific book you are referring to",
            "could you clarify the title or author",
            "which book you're asking about",
            "which book you are asking about",
            "search results only provide a short excerpt",
            "give you a more accurate and detailed summary",
        )
        if any(marker in lowered for marker in markers):
            return True

        return (
            "clarify" in lowered
            and any(
                marker in lowered
                for marker in ("book", "document", "title", "author")
            )
        )

    @staticmethod
    def _looks_like_summary_format_description_response(text: str) -> bool:
        """Return True for meta descriptions of a summary format."""
        lowered = " ".join(str(text or "").lower().split())
        if not lowered:
            return False

        if not lowered.startswith(
            (
                "a bulleted list of ",
                "a bullet list of ",
                "a brief bulleted list of ",
                "a concise bulleted list of ",
                "a list of ",
            )
        ):
            return False

        excerpt_markers = (
            "snippet",
            "excerpt",
            "text",
            "document",
            "key elements",
            "key details",
        )
        label_markers = (
            "setting",
            "topic",
            "characters",
            "action",
            "context",
            "tone",
            "premise",
            "conflict",
            "themes",
        )
        return (
            any(marker in lowered for marker in excerpt_markers)
            and sum(marker in lowered for marker in label_markers) >= 3
        )

    @staticmethod
    def _looks_like_draft_claim_analysis_response(text: str) -> bool:
        """Return True for verifier draft-claim/evidence analysis blocks."""
        lowered = " ".join(str(text or "").lower().split())
        if not lowered:
            return False

        if "evaluate the draft vs. evidence" in lowered:
            return True

        has_draft_claim = "draft claim" in lowered or "draft answer" in lowered
        has_evidence = "evidence:" in lowered or "**evidence:**" in lowered
        return has_draft_claim and has_evidence

    @staticmethod
    def _looks_like_malformed_forced_response_fragment(text: str) -> bool:
        """Return True for tiny prompt-tail fragments, not user answers."""
        normalized = " ".join(str(text or "").split())
        if not normalized:
            return False

        if not any(char.isalnum() for char in normalized):
            return True

        lowered = normalized.lower()
        if any(
            marker in lowered for marker in ("draft:", "answer:", "response:")
        ):
            if len(normalized) <= 80:
                return True
            if normalized[:1] in {'"', "'", ",", ".", ")"}:
                return True

        alpha_chars = sum(1 for char in normalized if char.isalpha())
        if len(normalized) <= 24 and alpha_chars < 8:
            if any(char in normalized for char in ('"', "'", "(", ")", ",")):
                return True

        return False

    @staticmethod
    def _looks_like_verification_verdict_response(text: str) -> bool:
        """Return True when text is a verifier verdict, not a user answer."""
        normalized = " ".join(str(text or "").split())
        if not normalized:
            return False

        normalized_for_split = re.sub(r'([.!?])["\'”)]\s+', r"\1 ", normalized)
        sentences = [
            sentence.strip(' "\'“”')
            for sentence in re.split(r"(?<=[.!?])\s+", normalized_for_split)
            if sentence.strip()
        ]
        if len(sentences) < 2:
            return False

        verdict = sentences[-1].rstrip(".!?").lower()
        for phrase in (
            "by evidence",
            "by the evidence",
            "by context",
            "by the context",
            "by text",
            "by the text",
            "by the excerpt",
            "by the document excerpt",
        ):
            verdict = verdict.replace(phrase, " ")
        verdict = re.sub(r"^[\W_]+|[\W_]+$", "", verdict)
        verdict = re.sub(r"[\[\](){}<>\"'`*_•✓→:;,.!?-]+", " ", verdict)
        verdict = " ".join(verdict.split())
        if verdict not in {
            "supported",
            "not supported",
            "partially supported",
            "largely supported",
            "mostly supported",
            "unsupported",
            "contradicted",
            "inconclusive",
        }:
            return False

        evidence_markers = (
            normalized[:1] in {'"', "'", "“"}
            or any(
                marker in normalized.lower()
                for marker in ("claim:", "evidence:", "excerpt:", "the claim")
            )
        )
        return evidence_markers or len(sentences) <= 2

    @staticmethod
    def _looks_like_structure_only_response(text: str) -> bool:
        """Return True for table-of-contents style answers."""
        normalized = " ".join(str(text or "").split())
        if not normalized:
            return False

        upper = normalized.upper()
        marker_hits = sum(
            1
            for marker in (
                "INTRODUCTION",
                "PROLOGUE",
                "THE BOOK OF",
                "BOOK OF",
                "CHAPTER ",
                "PART ",
            )
            if marker in upper
        )
        if marker_hits < 2:
            return False

        alpha_chars = [char for char in normalized if char.isalpha()]
        if not alpha_chars:
            return False
        uppercase_ratio = sum(1 for char in alpha_chars if char.isupper()) / len(
            alpha_chars
        )
        has_sentence_punctuation = any(mark in normalized for mark in (".", "!", "?"))
        return uppercase_ratio >= 0.6 and not has_sentence_punctuation

    @staticmethod
    def _looks_like_summary_label_inventory_response(text: str) -> bool:
        """Return True for bare summary category labels without prose."""
        normalized = " ".join(str(text or "").split())
        if not normalized:
            return False

        label_markers = {
            "premise",
            "setting",
            "conflict",
            "central conflict",
            "characters",
            "character relationships",
            "relationships",
            "themes",
            "plot",
            "subject",
            "argument",
            "context",
        }
        parts = [
            part.strip(" .:;!?-\t").lower()
            for part in re.split(r"[,;/]", normalized)
            if part.strip(" .:;!?-\t")
        ]
        if len(parts) < 2 or len(parts) > 6:
            return False

        return all(part in label_markers for part in parts)

    @classmethod
    def _looks_like_summary_scaffolding_response(cls, text: str) -> bool:
        """Return True for summary candidates that are structure or inventory."""
        if cls._looks_like_structure_only_response(text):
            return True
        if cls._looks_like_summary_label_inventory_response(text):
            return True

        lines = [line.strip() for line in str(text or "").splitlines() if line.strip()]
        if len(lines) < 2:
            return False

        list_lines = [
            line for line in lines if re.match(r"^(?:[-*+]\s+|\d+\.\s+)", line)
        ]
        if len(list_lines) < 2:
            return False

        excerpt_line_hits = sum(
            1
            for line in list_lines
            if re.search(r"\bexcerpt\s+\d+", line, flags=re.IGNORECASE)
        )
        if excerpt_line_hits >= 2:
            return True

        lowered = "\n".join(lines).lower()
        markers = ("document:", "excerpt ", "matched documents", "relevant excerpts")
        return sum(marker in lowered for marker in markers) >= 2