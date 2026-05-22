"""Response normalization helpers for node functions."""

import re


class ResponseNormalizationMixin:
    """Normalize recovered reasoning text into visible response prose."""

    @classmethod
    def _clean_reasoning_candidate(cls, paragraph: str) -> str:
        """Normalize one fallback reasoning paragraph into visible text."""
        candidate = paragraph.strip()
        if not candidate:
            return ""
        if re.search(
            r"(?:^|\n)\s*\*\s+\*(?:final answer|critique|draft|review|constraint)[^*]*:\*",
            candidate,
            flags=re.IGNORECASE,
        ):
            return ""
        if candidate[:1] == candidate[-1:] and candidate[:1] in {'"', "'"}:
            candidate = candidate[1:-1].strip()
        candidate = cls._strip_forced_response_label(candidate)
        section_body_match = re.match(
            r"^\d+\.\s+\*\*[^*]+:\*\*\s*(.+)$",
            candidate,
            flags=re.DOTALL,
        )
        if section_body_match:
            candidate = section_body_match.group(1).strip()
        if cls._looks_like_instruction_reflection(candidate):
            return ""
        if cls._looks_like_summary_prompt_echo(candidate):
            return ""
        if cls._looks_like_search_result_preface_response(candidate):
            return ""
        if cls._looks_like_summary_direction_response(candidate):
            return ""
        if cls._looks_like_document_summary_clarification_response(candidate):
            return ""
        if cls._looks_like_summary_format_description_response(candidate):
            return ""
        if cls._looks_like_reasoning_header(candidate):
            return ""
        if cls._looks_like_verification_verdict_response(candidate):
            return ""
        return candidate

    @staticmethod
    def _normalize_inventory_summary_response(text: str) -> str:
        """Flatten one list-style excerpt inventory into short prose."""
        fragments: list[str] = []
        for raw_line in str(text or "").splitlines():
            line = raw_line.strip()
            if not line:
                continue
            line = re.sub(r"^(?:[-*+]\s+|\d+\.\s+)", "", line).strip()
            if not line:
                continue
            if line.lower().startswith("document:"):
                line = line.split(":", 1)[-1].strip()
            elif ":" in line and line.lower().startswith("excerpt "):
                line = line.split(":", 1)[-1].strip()
            if not line:
                continue
            if line[-1] not in ".!?":
                line = f"{line}."
            if line not in fragments:
                fragments.append(line)

        if not fragments:
            return ""
        return " ".join(fragments)

    @classmethod
    def _normalize_numbered_summary_response(cls, text: str) -> str:
        """Flatten one numbered reasoning list into plain summary prose."""
        fragments: list[str] = []
        for raw_line in str(text or "").splitlines():
            match = re.match(r"^\s*\d+\.\s+(.+)$", raw_line)
            if not match:
                continue
            line = cls._clean_reasoning_candidate(match.group(1).strip())
            if not line:
                continue

            lowered = line.lower()
            if any(
                marker in lowered
                for marker in (
                    "constraint",
                    "instruction",
                    "review against constraints",
                    "do not call another tool",
                    "respond now",
                )
            ):
                continue

            if line[-1] not in ".!?":
                line = f"{line}."
            if line not in fragments:
                fragments.append(line)

        if len(fragments) < 2:
            return ""
        return " ".join(fragments)

    @staticmethod
    def _looks_like_reasoning_header(candidate: str) -> bool:
        """Return True when text is a planning header, not a user answer."""
        lowered = candidate.strip().lower()
        normalized = re.sub(r"[*_`]+", "", lowered)
        normalized = " ".join(normalized.split())
        if normalized in {
            "thinking process:",
            "drafting the response:",
            "refining for conciseness and flow:",
            "final review against constraints:",
            "analyze the request:",
            "analyze the search results:",
            "synthesize the answer:",
        }:
            return True
        scaffolding_labels = (
            "thinking process",
            "analyze the request",
            "analyze the evidence",
            "analyze the search results",
            "draft the response",
            "drafting the response",
            "drafting - step 1",
            "drafting - step 2",
            "mental outline",
            "writing & counting",
            "refine the response",
            "refining for conciseness and flow",
            "final review against constraints",
            "final polish",
            "synthesize the answer",
        )
        if normalized.endswith(":"):
            residual = normalized
            for label in scaffolding_labels:
                residual = residual.replace(label, " ")
            residual = re.sub(r"[\d\W_]+", " ", residual)
            residual_words = [
                word for word in residual.split() if word not in {"and", "the", "step"}
            ]
            if any(label in normalized for label in scaffolding_labels):
                if len(residual_words) <= 3:
                    return True
        marker_hits = sum(label in normalized for label in scaffolding_labels)
        if marker_hits >= 2:
            residual = normalized
            for label in scaffolding_labels:
                residual = residual.replace(label, " ")
            residual = re.sub(r"[\d\W_]+", " ", residual)
            residual_words = [
                word for word in residual.split() if word not in {"and", "the", "step"}
            ]
            if len(residual_words) <= 3:
                return True
        reasoning_markers = (
            "task:",
            "constraint 1:",
            "constraint 2:",
            "constraint 3:",
            "constraint 4:",
            "constraint 5:",
            "constraint 6:",
            "input:",
            "constraints check:",
            "natural/conversational?",
            "identify document first?",
            "only search result info?",
            "no tools/json?",
            "concise?",
            "self-correction",
            "wait, one more check:",
            "review against constraints",
            "4-6 sentences? yes",
            "one or two short paragraphs? yes",
            "no bullet points? yes",
            "conversational? yes",
            "specific details? yes",
        )
        if any(marker in lowered for marker in reasoning_markers):
            return True
        if re.match(r"^\d+\.\s+\*\*.*\*\*$", candidate):
            return True
        if re.match(r"^\d+\.\s+\*\*.*?:\*\*", candidate):
            return True
        return False