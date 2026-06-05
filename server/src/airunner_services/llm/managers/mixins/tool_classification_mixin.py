"""Tool routing heuristics and LLM-assisted classification."""

from __future__ import annotations

import re
from typing import Any, List, Optional, Tuple

from langchain_core.messages import HumanMessage

from airunner_services.llm.core.tool_registry import ToolCategory
from airunner_services.llm.thinking_parser import (
    detect_thinking_close_tag,
    detect_thinking_open_tag,
    extract_thinking_and_response,
)
from airunner_services.llm.utils.stream_debug import print_stream_debug
from airunner_services.llm_workflow_events import (
    resolve_llm_workflow_event_sink,
)


class ToolClassificationMixin:
    """Classify prompts into tool categories and direct tool routes."""

    ALWAYS_INCLUDE_CATEGORIES = {"knowledge"}
    SIMPLE_SYSTEM_TOOL_PATTERNS: Tuple[Tuple[str, str], ...] = (
        (r"\bwhat\s+time\s+is\s+it\b", "get_current_datetime"),
        (
            r"\bwhat(?:'s| is)?\s+the\s+(?:current\s+)?time\b",
            "get_current_datetime",
        ),
        (
            r"\btell\s+me\s+the\s+(?:current\s+)?time\b",
            "get_current_datetime",
        ),
        (r"\bcurrent\s+date\s+and\s+time\b", "get_current_datetime"),
        (
            r"\bwhat(?:'s| is)?\s+(?:today'?s\s+)?date\b",
            "get_current_datetime",
        ),
        (
            r"\bwhat(?:'s| is)?\s+the\s+current\s+date\b",
            "get_current_datetime",
        ),
        (r"\bwhat\s+day\s+is\s+it\b", "get_current_datetime"),
        (r"\btoday'?s\s+date\b", "get_current_datetime"),
        (r"\bdate\s+and\s+time\b", "get_current_datetime"),
    )
    SIMPLE_GREETING_PATTERNS: Tuple[str, ...] = (
        r"^\s*hello[!.?,\s]*$",
        r"^\s*hi[!.?,\s]*$",
        r"^\s*hey[!.?,\s]*$",
        r"^\s*yo[!.?,\s]*$",
        r"^\s*sup[!.?,\s]*$",
        r"^\s*good\s+morning[!.?,\s]*$",
        r"^\s*good\s+afternoon[!.?,\s]*$",
        r"^\s*good\s+evening[!.?,\s]*$",
        r"^\s*thanks[!.?,\s]*$",
        r"^\s*thank\s+you[!.?,\s]*$",
    )
    SIMPLE_NO_TOOL_PATTERNS: Tuple[str, ...] = (
        r"^\s*how\s+are\s+you[!.?,\s]*$",
        r"^\s*who\s+are\s+you[!.?,\s]*$",
        r"^\s*what(?:'s|\s+is)\s+your\s+name[!.?,\s]*$",
        r"^\s*what\s+can\s+you\s+do[!.?,\s]*$",
        r"^\s*(?:tell\s+me\s+another|another\s+one)\b.*$",
        r"^\s*(?:like\s+what|for\s+example)[!.?,\s]*$",
        r"^\s*(?:can\s+you\s+)?tell\s+me\s+" r"(?:a|another)?\s*joke\b.*$",
        r"^\s*(?:please\s+)?(?:tell\s+me|write\s+me|make\s+up)\s+"
        r"(?:a|another)?\s*(?:story|poem|haiku|riddle)\b.*$",
        r"^\s*(?:give\s+me|share)\s+(?:a\s+)?" r"(?:fun\s+fact|quote)\b.*$",
        r"^\s*(?:make\s+me\s+laugh|be\s+funny)[!.?,\s]*$",
    )
    CONSTRAINED_REPLY_HINTS: Tuple[str, ...] = (
        "single digit",
        "one digit",
        "single character",
        "one character",
        "single letter",
        "one letter",
        "single word",
        "one word",
    )
    SEARCH_TRIGGER_WORDS: Tuple[str, ...] = (
        "search",
        "look up",
        "lookup",
        "find",
        "google",
        "bing",
        "duckduckgo",
        "ddg",
        "web",
        "internet",
        "news",
        "latest",
        "recent",
    )

    @classmethod
    def _detect_simple_tool_route(
        cls,
        prompt: str,
    ) -> Tuple[Optional[List[str]], Optional[str]]:
        """Detect trivial prompts that should call a single tool."""
        prompt_lc = (prompt or "").strip().lower()
        if not prompt_lc:
            return None, None

        for pattern, tool_name in cls.SIMPLE_SYSTEM_TOOL_PATTERNS:
            if re.search(pattern, prompt_lc):
                return ["system"], tool_name

        return None, None

    @classmethod
    def _is_simple_greeting_prompt(cls, prompt: str) -> bool:
        """Return True for trivial greeting-style prompts."""
        prompt_lc = (prompt or "").strip().lower()
        if not prompt_lc or len(prompt_lc) > 40:
            return False

        return any(
            re.match(pattern, prompt_lc)
            for pattern in cls.SIMPLE_GREETING_PATTERNS
        )

    @classmethod
    def _is_simple_no_tool_prompt(cls, prompt: str) -> bool:
        """Return True for casual prompts that should avoid tools."""
        prompt_lc = (prompt or "").strip().lower()
        if not prompt_lc or len(prompt_lc) > 120:
            return False

        return any(
            re.match(pattern, prompt_lc)
            for pattern in cls.SIMPLE_NO_TOOL_PATTERNS
        )

    @classmethod
    def _is_constrained_reply_prompt(cls, prompt: str) -> bool:
        """Return True for strict reply-shape prompts needing no tools."""
        prompt_lc = re.sub(r"^\s*/no_think\s*", "", (prompt or "").lower())
        prompt_lc = prompt_lc.strip()
        if not prompt_lc or len(prompt_lc) > 160:
            return False
        if not re.match(r"^(?:reply|respond)\s+with\b", prompt_lc):
            return False
        return any(hint in prompt_lc for hint in cls.CONSTRAINED_REPLY_HINTS)

    @classmethod
    def _has_search_trigger_prompt(cls, prompt: str) -> bool:
        """Return True when a prompt clearly requests search tools."""
        prompt_lc = (prompt or "").strip().lower()
        return any(
            trigger in prompt_lc for trigger in cls.SEARCH_TRIGGER_WORDS
        )

    @classmethod
    def _should_disable_thinking_for_prompt(
        cls,
        prompt: str,
        selected_categories: Optional[List[str]] = None,
        force_tool: Optional[str] = None,
    ) -> bool:
        """Return True when reasoning adds latency but little value."""
        if force_tool:
            return True
        if cls._is_simple_greeting_prompt(prompt):
            return True
        if selected_categories == [] and len((prompt or "").strip()) <= 40:
            return True
        return False

    @staticmethod
    def _split_classification_response(
        response_text: str,
        additional_kwargs: Optional[dict] = None,
    ) -> Tuple[Optional[str], str]:
        """Return classifier thinking text and visible category text."""
        reasoning_text = ""
        if additional_kwargs:
            reasoning_text = additional_kwargs.get("reasoning_content") or ""
        tagged_thinking, visible_text = extract_thinking_and_response(
            response_text
        )
        if tagged_thinking and not reasoning_text:
            reasoning_text = tagged_thinking
        cleaned_thinking = reasoning_text.strip() or None
        return cleaned_thinking, visible_text

    @staticmethod
    def _classification_candidates(response_text: str) -> list[str]:
        """Return normalized classifier candidates without assistant labels."""
        normalized = re.sub(
            r"categories:\s*[a-z,\s]+",
            "",
            (response_text or "").strip().lower(),
            flags=re.IGNORECASE,
        )
        candidates = []
        for line in normalized.splitlines():
            candidate = line.strip()
            if candidate in {"", "assistant", "assistant:"}:
                continue
            if candidate.startswith("assistant:"):
                candidate = candidate[len("assistant:") :].strip()
            elif candidate.startswith("assistant "):
                candidate = candidate[len("assistant ") :].strip()
            if candidate:
                candidates.append(candidate)
        return candidates or ([normalized] if normalized else [])

    @staticmethod
    def _parse_selected_categories(
        candidate_text: str,
        available_categories: list[str],
    ) -> list[str]:
        """Parse one normalized classifier response into tool categories."""
        selected_categories = []
        for cat in candidate_text.split(","):
            token = cat.strip()
            if (
                token in available_categories
                and token not in selected_categories
            ):
                selected_categories.append(token)
        if selected_categories:
            return selected_categories[:5]
        for token in candidate_text.replace(",", " ").split():
            token_clean = token.strip().strip(".;:")
            if (
                token_clean in available_categories
                and token_clean not in selected_categories
            ):
                selected_categories.append(token_clean)
        return selected_categories[:5]

    def _emit_classification_thinking_event(
        self,
        status: str,
        content: str,
        request_id: Optional[str],
    ) -> None:
        """Emit one live classification-thinking update."""
        event_sink = resolve_llm_workflow_event_sink(self)
        if not getattr(event_sink, "active", False):
            return
        event_sink.emit_thinking(
            {
                "status": status,
                "content": content,
                "request_id": request_id,
            }
        )

    def _append_classification_thinking(
        self,
        state: dict[str, Any],
        content: str,
        allow_thinking: bool,
        request_id: Optional[str],
    ) -> None:
        """Accumulate and optionally stream one classification delta."""
        if not content:
            return
        state["thinking_parts"].append(content)
        if not allow_thinking:
            return
        if not state["thinking_started"]:
            self._emit_classification_thinking_event(
                "started",
                "",
                request_id,
            )
            state["thinking_started"] = True
        self._emit_classification_thinking_event(
            "streaming",
            content,
            request_id,
        )

    def _finish_classification_thinking(
        self,
        state: dict[str, Any],
        allow_thinking: bool,
        request_id: Optional[str],
    ) -> None:
        """Finish one streamed classification-thinking block."""
        if not state["in_thinking_block"]:
            return
        state["in_thinking_block"] = False
        state["thinking_tag_format"] = ""
        if not allow_thinking or not state["thinking_started"]:
            return
        self._emit_classification_thinking_event(
            "completed",
            "".join(state["thinking_parts"]),
            request_id,
        )

    def _consume_classification_stream_text(
        self,
        state: dict[str, Any],
        text: str,
        allow_thinking: bool,
        request_id: Optional[str],
    ) -> None:
        """Split one streamed classification chunk into thinking and text."""
        remaining = text
        while remaining:
            if state["in_thinking_block"]:
                found_close, before_close, after_close = (
                    detect_thinking_close_tag(
                        remaining,
                        state["thinking_tag_format"],
                    )
                )
                if not found_close:
                    self._append_classification_thinking(
                        state,
                        remaining,
                        allow_thinking,
                        request_id,
                    )
                    return
                self._append_classification_thinking(
                    state,
                    before_close,
                    allow_thinking,
                    request_id,
                )
                self._finish_classification_thinking(
                    state,
                    allow_thinking,
                    request_id,
                )
                remaining = after_close
                continue

            found_open, tag_format, before_open, after_open = (
                detect_thinking_open_tag(remaining)
            )
            if not found_open:
                state["visible_parts"].append(remaining)
                return
            if before_open:
                state["visible_parts"].append(before_open)
            state["in_thinking_block"] = True
            state["thinking_tag_format"] = tag_format
            remaining = after_open

    def _stream_classification_response(
        self,
        chat_model: Any,
        classification_prompt: str,
        allow_thinking: bool,
    ) -> Tuple[Optional[str], str]:
        """Return streamed classification thinking and visible text."""
        request_id = getattr(self, "_current_request_id", None)
        state = {
            "in_thinking_block": False,
            "thinking_started": False,
            "thinking_tag_format": "",
            "thinking_parts": [],
            "visible_parts": [],
        }
        for chunk in chat_model.stream(
            [HumanMessage(content=classification_prompt)]
        ):
            chunk_message = getattr(chunk, "message", chunk)
            text = getattr(chunk_message, "content", "") or ""
            additional_kwargs = (
                getattr(chunk_message, "additional_kwargs", {}) or {}
            )
            reasoning_delta = additional_kwargs.get(
                "thinking_content"
            ) or additional_kwargs.get("reasoning_content")
            self._append_classification_thinking(
                state,
                reasoning_delta or "",
                allow_thinking,
                request_id,
            )
            if text:
                self._consume_classification_stream_text(
                    state,
                    text,
                    allow_thinking,
                    request_id,
                )
        self._finish_classification_thinking(
            state,
            allow_thinking,
            request_id,
        )
        thinking_text = "".join(state["thinking_parts"]).strip() or None
        response_text = "".join(state["visible_parts"])
        if thinking_text or not response_text:
            return thinking_text, response_text
        return self._split_classification_response(response_text)

    def _invoke_classification_response(
        self,
        chat_model: Any,
        classification_prompt: str,
    ) -> Tuple[Optional[str], str]:
        """Return one non-streamed classification response."""
        response = chat_model.invoke(
            [HumanMessage(content=classification_prompt)]
        )
        return self._split_classification_response(
            getattr(response, "content", "") or "",
            getattr(response, "additional_kwargs", {}) or {},
        )

    def _classify_prompt_for_tools(
        self,
        prompt: str,
        allow_thinking: bool = True,
    ) -> list:
        """Use the active model to classify tool needs."""
        available_categories = [cat.value for cat in ToolCategory]
        prompt_directive = "" if allow_thinking else "/no_think\n"
        classification_prompt = f"""{prompt_directive}
Classify which tool categories are needed for this user message.

Categories: {', '.join(available_categories)}

Message: \"{prompt[:500]}\"

Reply with ONLY category names (comma-separated) or \"none\":"""

        try:
            if self._workflow_manager and hasattr(
                self._workflow_manager,
                "_original_chat_model",
            ):
                chat_model = self._workflow_manager._original_chat_model
                if chat_model:
                    original_thinking = getattr(
                        chat_model,
                        "enable_thinking",
                        True,
                    )
                    if hasattr(chat_model, "enable_thinking"):
                        chat_model.enable_thinking = allow_thinking

                    original_temp = getattr(chat_model, "temperature", 0.7)
                    if hasattr(chat_model, "temperature"):
                        chat_model.temperature = 0.1

                    original_tool_choice = getattr(
                        chat_model,
                        "tool_choice",
                        None,
                    )
                    if hasattr(chat_model, "tool_choice"):
                        chat_model.tool_choice = "none"

                    try:
                        if allow_thinking:
                            thinking_text, response_text = (
                                self._stream_classification_response(
                                    chat_model,
                                    classification_prompt,
                                    allow_thinking,
                                )
                            )
                        else:
                            thinking_text, response_text = (
                                self._invoke_classification_response(
                                    chat_model,
                                    classification_prompt,
                                )
                            )
                    finally:
                        if hasattr(chat_model, "enable_thinking"):
                            chat_model.enable_thinking = original_thinking
                        if hasattr(chat_model, "temperature"):
                            chat_model.temperature = original_temp
                        if hasattr(chat_model, "tool_choice"):
                            chat_model.tool_choice = original_tool_choice

                    print_stream_debug(
                        "tool_classification.response",
                        original_enable_thinking=original_thinking,
                        requested_enable_thinking=allow_thinking,
                        prompt_no_think=not allow_thinking,
                        content=response_text,
                        reasoning_content=thinking_text,
                    )

                    candidate_texts = self._classification_candidates(
                        response_text
                    )
                    candidate_text = (
                        candidate_texts[0] if candidate_texts else ""
                    )
                    self.logger.info(
                        "LLM classification response: %s",
                        candidate_text,
                    )
                    if candidate_text == "none" or not candidate_text:
                        self.logger.info(
                            "Auto mode: LLM determined no tools needed"
                        )
                        return []

                    selected_categories = []
                    for candidate in candidate_texts:
                        selected_categories = self._parse_selected_categories(
                            candidate,
                            available_categories,
                        )
                        if selected_categories:
                            break

                    if not selected_categories and len(candidate_texts) > 1:
                        selected_categories = self._parse_selected_categories(
                            " ".join(candidate_texts),
                            available_categories,
                        )

                    if not selected_categories:
                        self.logger.info(
                            "Auto mode: No valid categories parsed, defaulting "
                            "to search"
                        )
                        selected_categories = ["search"]

                    self.logger.info(
                        "Auto mode (LLM): Selected %s categories: %s",
                        len(selected_categories),
                        selected_categories,
                    )
                    return selected_categories
        except Exception as exc:
            self.logger.warning(
                "LLM classification failed: %s, falling back to all tools",
                exc,
            )

        self.logger.info(
            "Auto mode: Classification unavailable, providing broad tool "
            "access"
        )
        return ["search", "knowledge", "system", "math"]

    def _should_use_harness(self, prompt: str) -> bool:
        """Check if a prompt should use the long-running harness."""
        try:
            from airunner_services.llm.long_running import should_use_harness

            use_harness, analysis = should_use_harness(prompt)
            if use_harness and analysis:
                self.logger.info(
                    "Harness recommended: %s (confidence: %.2f) - %s",
                    analysis.task_type.value,
                    analysis.confidence,
                    analysis.reason,
                )
            return use_harness
        except ImportError:
            self.logger.debug("Long-running harness not available")
            return False
        except Exception as exc:
            self.logger.warning(
                "Error checking harness applicability: %s",
                exc,
            )
            return False
