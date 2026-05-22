"""LLM-driven request preprocessing for tool selection."""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

from airunner.components.llm.managers.request_plan import RequestPlan


class ToolClassificationMixin:
    """Preprocess requests with the active LLM before the main flow."""

    ALWAYS_INCLUDE_CATEGORIES = {"knowledge"}
    REQUEST_PREPROCESS_HISTORY_LIMIT = 8
    REQUEST_PREPROCESS_MESSAGE_CHAR_LIMIT = 320
    DOCUMENT_TOOL_NAMES = {
        "inspect_loaded_documents",
        "analyze_loaded_document",
        "rag_search",
    }
    VALID_DOCUMENT_INTENTS = {
        "identity",
        "structure",
        "summary",
        "compare",
        "extract",
        "list",
        "transform",
        "retrieval",
    }
    VALID_DOCUMENT_SUMMARY_FOCI = {"overview", "premise"}
    VALID_DOCUMENT_ANSWER_MODES = {"deterministic", "synthesized"}
    VALID_PLANNER_MODES = {"select_tools"}
    VALID_ANSWER_STRATEGIES = {"direct", "compose"}
    VALID_FINALIZATION_MODES = {
        "direct_response",
        "compose_and_verify",
    }

    @staticmethod
    def _derive_document_answer_mode(
        document_intent: Optional[str],
    ) -> Optional[str]:
        """Return one document answer mode derived from intent."""
        if document_intent in {"identity", "structure"}:
            return "deterministic"
        if document_intent:
            return "synthesized"
        return None

    @staticmethod
    def _derive_document_primary_tool(
        document_intent: Optional[str],
        *,
        rag_file_count: int,
    ) -> Optional[str]:
        """Return one first tool inferred from request-scoped intent."""
        if document_intent in {"identity", "structure"}:
            return "inspect_loaded_documents"
        if document_intent == "summary":
            if rag_file_count == 1:
                return "analyze_loaded_document"
            return "rag_search"
        if document_intent in {
            "compare",
            "extract",
            "list",
            "transform",
            "retrieval",
        }:
            return "rag_search"
        return None

    @staticmethod
    def _derive_answer_strategy(
        *,
        tool_required: bool,
        document_answer_mode: Optional[str],
    ) -> Optional[str]:
        """Return one normalized answer strategy for the request plan."""
        if document_answer_mode == "deterministic":
            return "direct"
        if tool_required:
            return "compose"
        return None

    @staticmethod
    def _derive_finalization_mode(
        *,
        document_answer_mode: Optional[str],
    ) -> Optional[str]:
        """Return one normalized finalization mode for the request plan."""
        if document_answer_mode == "deterministic":
            return "direct_response"
        if document_answer_mode == "synthesized":
            return "compose_and_verify"
        return None

    @staticmethod
    def _normalize_optional_token(value: Any) -> Optional[str]:
        """Return one normalized string token or None."""
        if not isinstance(value, str):
            return None
        normalized = value.strip().lower()
        if not normalized or normalized == "none":
            return None
        return normalized

    @classmethod
    def _normalize_string_list(cls, value: Any) -> List[str]:
        """Return one normalized list of unique lowercase strings."""
        if isinstance(value, str):
            items = [item.strip() for item in value.split(",")]
        elif isinstance(value, list):
            items = value
        else:
            return []

        normalized: List[str] = []
        for item in items:
            if not isinstance(item, str):
                continue
            token = cls._normalize_optional_token(item)
            if token and token not in normalized:
                normalized.append(token)
        return normalized

    @staticmethod
    def _strip_reasoning_markup(text: str) -> str:
        """Remove common reasoning wrappers before JSON parsing."""
        cleaned = str(text or "")
        cleaned = re.sub(
            r"<think>.*?</think>",
            "",
            cleaned,
            flags=re.DOTALL | re.IGNORECASE,
        )
        cleaned = re.sub(
            r"\[THINK\].*?\[/THINK\]",
            "",
            cleaned,
            flags=re.DOTALL | re.IGNORECASE,
        )
        cleaned = re.sub(
            r"\[/?THINK\]",
            "",
            cleaned,
            flags=re.IGNORECASE,
        )
        return cleaned.strip()

    @classmethod
    def _extract_json_object(cls, text: str) -> Optional[Dict[str, Any]]:
        """Return the first valid JSON object found in model output."""
        candidates = [cls._strip_reasoning_markup(text)]
        fenced_blocks = re.findall(
            r"```json\s*(\{.*?\})\s*```",
            text,
            flags=re.DOTALL | re.IGNORECASE,
        )
        candidates.extend(fenced_blocks)

        stripped = cls._strip_reasoning_markup(text)
        start = stripped.find("{")
        end = stripped.rfind("}")
        if start != -1 and end != -1 and end > start:
            candidates.append(stripped[start : end + 1])

        seen = set()
        for candidate in candidates:
            candidate = str(candidate or "").strip()
            if not candidate or candidate in seen:
                continue
            seen.add(candidate)
            try:
                payload = json.loads(candidate)
            except Exception:
                continue
            if isinstance(payload, dict):
                return payload
        return None

    def _get_preprocess_tool_inventory(self) -> List[Dict[str, str]]:
        """Return one compact inventory of currently available tools."""
        inventory: List[Dict[str, str]] = []
        seen_names: set[str] = set()

        tool_manager = getattr(self, "_tool_manager", None)
        if tool_manager is not None:
            try:
                tools = tool_manager.get_all_tools(include_deferred=True)
            except Exception:
                tools = []
            for tool in tools:
                name = getattr(tool, "name", getattr(tool, "__name__", None))
                if not isinstance(name, str) or not name or name in seen_names:
                    continue
                seen_names.add(name)
                category = getattr(tool, "category", None)
                if hasattr(category, "value"):
                    category = category.value
                inventory.append(
                    {
                        "name": name,
                        "category": str(category or "").strip().lower(),
                        "description": str(
                            getattr(tool, "description", "") or ""
                        ).strip(),
                    }
                )

        if inventory:
            return sorted(
                inventory,
                key=lambda item: (item["category"], item["name"]),
            )

        from airunner.components.llm.core.tool_registry import ToolRegistry

        for tool_info in ToolRegistry.all().values():
            if tool_info.name in seen_names:
                continue
            seen_names.add(tool_info.name)
            inventory.append(
                {
                    "name": tool_info.name,
                    "category": tool_info.category.value,
                    "description": str(tool_info.description or "").strip(),
                }
            )
        return sorted(
            inventory,
            key=lambda item: (item["category"], item["name"]),
        )

    def _serialize_recent_conversation(
        self,
        conversation: Any,
    ) -> str:
        """Return one compact recent conversation transcript."""
        history_manager = getattr(self, "_conversation_history_manager", None)
        if history_manager is None or conversation is None:
            return ""

        try:
            history = history_manager.load_conversation_history(
                conversation=conversation,
                max_messages=self.REQUEST_PREPROCESS_HISTORY_LIMIT,
            )
        except Exception:
            return ""

        lines: List[str] = []
        for message in history[-self.REQUEST_PREPROCESS_HISTORY_LIMIT :]:
            if not isinstance(message, dict):
                continue
            content = " ".join(
                str(message.get("content", "") or "").split()
            )
            if not content:
                continue
            role = "Assistant" if message.get("is_bot") else "User"
            lines.append(
                f"{role}: {content[: self.REQUEST_PREPROCESS_MESSAGE_CHAR_LIMIT]}"
            )
        return "\n".join(lines)

    @staticmethod
    def _serialize_document_capabilities(llm_request: Any) -> str:
        """Return one compact description of attached-document metadata."""
        capabilities = getattr(llm_request, "attached_document_capabilities", [])
        if not capabilities:
            return ""

        lines = []
        for capability in capabilities[:4]:
            if not isinstance(capability, dict):
                continue
            name = str(capability.get("file_name", "") or "").strip()
            estimated_tokens = capability.get("estimated_tokens")
            fits_context = capability.get("fits_current_context")
            if not name:
                continue
            lines.append(
                f"- {name} | estimated_tokens={estimated_tokens} "
                f"| fits_current_context={fits_context}"
            )
        return "\n".join(lines)

    def _build_request_preprocess_prompt(
        self,
        prompt: str,
        *,
        action: Any,
        llm_request: Any,
        conversation: Any,
    ) -> str:
        """Build the internal prompt for request preprocessing."""
        tool_inventory = self._get_preprocess_tool_inventory()
        categories = sorted(
            {item["category"] for item in tool_inventory if item["category"]}
        )
        tool_lines = [
            f"- {item['name']} [{item['category'] or 'uncategorized'}]: "
            f"{item['description']}"
            for item in tool_inventory
        ]
        conversation_text = self._serialize_recent_conversation(conversation)
        document_capabilities = self._serialize_document_capabilities(
            llm_request
        )
        action_name = getattr(action, "name", str(action or "unknown"))
        rag_files = getattr(llm_request, "rag_files", []) or []

        sections = [
            "You are AIRunner's internal request preprocessor.",
            "This is a private planning step before the main tool loop.",
            "Analyze the recent conversation and the latest user message.",
            "Rewrite the latest user message only if doing so makes it",
            "clearer, more self-contained, or easier to route.",
            "Then decide the smallest tool surface and the most likely first",
            "tool.",
            "Return ONLY JSON.",
            "",
            "Required JSON schema:",
            "{",
            '  "allowed_tool_names": ["analyze_loaded_document"],',
            '  "rewrite_needed": true,',
            '  "rewritten_query": "Provide a summary of the currently '
            'loaded document.",',
            '  "tool_required": true,',
            '  "tool_categories": ["rag"],',
            '  "primary_tool": "analyze_loaded_document",',
            '  "planner_mode": "none",',
            '  "planner_tool_hints": ["analyze_loaded_document"],',
            '  "document_query_intent": "summary",',
            '  "document_summary_focus": "premise",',
            '  "document_answer_mode": "synthesized",',
            '  "answer_strategy": "compose",',
            '  "finalization_mode": "compose_and_verify"',
            "}",
            "Rules:",
            "- Use [] for allowed_tool_names when no tool is needed.",
            "- Use [] for tool_categories when no tool is needed.",
            "- Use \"none\" for primary_tool, document_query_intent,",
            "  document_summary_focus, and document_answer_mode when they",
            "  do not apply.",
            "- Use \"none\" for planner_mode, answer_strategy, and",
            "  finalization_mode when they do not apply.",
            "- allowed_tool_names must contain only listed tool names.",
            "- planner_tool_hints must be [] when no tool is needed.",
            "- Categories must come from: " + ", ".join(categories),
            "- primary_tool must be one of the listed tool names or \"none\".",
            "- tool_categories must include the actual category of the",
            "  chosen primary_tool.",
            "- Use conversation context when the latest user message depends",
            "  on prior turns.",
            "- Keep rewritten_query concise and standalone.",
            "- Do not add explanations outside the JSON object.",
            "- If attached documents are present and the user refers to",
            "  \"this book\", \"this document\", \"this file\", or a",
            "  similar deictic reference, treat that as referring to the",
            "  attached document context instead of asking which document",
            "  they mean.",
            "- When exactly one document is attached and the user asks for",
            "  a broad explanation, summary, premise, or what the book is",
            "  about, prefer analyze_loaded_document as the first tool.",
            "- Use planner_mode \"select_tools\" only when more than one",
            "  document tool is genuinely needed or you cannot name a",
            "  single best first tool.",
            "",
            "Document tool guidance:",
            "- inspect_loaded_documents: document identity, title/author,",
            "  chapters, sections, and structure.",
            "- analyze_loaded_document: whole-document summary, premise/theme,",
            "  and broad document transformations when one document is loaded.",
            "- rag_search: localized fact lookup, quoted passages, excerpt",
            "  retrieval, and document-content fallback search.",
            "",
            "Document intent values:",
            "- identity, structure, summary, compare, extract, list,",
            "  transform, retrieval, none",
            "Document summary focus values:",
            "- overview, premise, none",
            "Document answer mode values:",
            "- deterministic, synthesized, none",
            "Planner mode values:",
            "- select_tools, none",
            "Answer strategy values:",
            "- direct, compose, none",
            "Finalization mode values:",
            "- direct_response, compose_and_verify, none",
            "",
            f"Current action: {action_name}",
            f"Attached documents: {len(rag_files)}",
        ]
        if document_capabilities:
            sections.extend(
                [
                    "Attached document capabilities:",
                    document_capabilities,
                ]
            )
        if conversation_text:
            sections.extend(["", "Recent conversation:", conversation_text])
        sections.extend(
            [
                "",
                "Latest user message:",
                str(prompt or "").strip(),
                "",
                "Available tools:",
                "\n".join(tool_lines),
            ]
        )
        return "\n".join(sections)

    def _invoke_request_preprocessor(self, prompt_text: str) -> Optional[str]:
        """Run the active chat model for request preprocessing."""
        from langchain_core.messages import HumanMessage

        chat_model = None
        workflow_manager = getattr(self, "_workflow_manager", None)
        if workflow_manager is not None:
            chat_model = getattr(workflow_manager, "_original_chat_model", None)
        if chat_model is None:
            chat_model = getattr(self, "_chat_model", None)
        if chat_model is None:
            return None

        original_values: List[tuple[str, Any]] = []
        for attr_name, override in (("tool_choice", "none"), ("tools", None)):
            if not hasattr(chat_model, attr_name):
                continue
            original_values.append((attr_name, getattr(chat_model, attr_name)))
            try:
                setattr(chat_model, attr_name, override)
            except Exception:
                continue

        if hasattr(chat_model, "temperature"):
            original_values.append(("temperature", getattr(chat_model, "temperature")))
            try:
                setattr(chat_model, "temperature", 0.1)
            except Exception:
                pass

        try:
            response = chat_model.invoke([HumanMessage(content=prompt_text)])
        finally:
            for attr_name, original_value in reversed(original_values):
                try:
                    setattr(chat_model, attr_name, original_value)
                except Exception:
                    continue

        return getattr(response, "content", str(response))

    def _derive_categories_for_tool(self, tool_name: str) -> List[str]:
        """Return one tool category list derived from the tool inventory."""
        normalized_name = self._normalize_optional_token(tool_name)
        if not normalized_name:
            return []
        for item in self._get_preprocess_tool_inventory():
            if item["name"].strip().lower() != normalized_name:
                continue
            category = self._normalize_optional_token(item.get("category"))
            return [category] if category else []
        return []

    def _ensure_primary_tool_categories(
        self,
        tool_categories: List[str],
        primary_tool: Optional[str],
    ) -> List[str]:
        """Ensure the chosen primary tool's category is available."""
        derived_categories = self._derive_categories_for_tool(primary_tool or "")
        if not derived_categories:
            return tool_categories
        merged = list(tool_categories)
        for category in derived_categories:
            if category not in merged:
                merged.append(category)
        return merged

    def _normalize_preprocess_payload(
        self,
        payload: Dict[str, Any],
        *,
        prompt: str,
        llm_request: Any,
    ) -> Dict[str, Any]:
        """Normalize one raw LLM preprocess payload."""
        rewritten_query = str(payload.get("rewritten_query", "") or "").strip()
        if not rewritten_query:
            rewritten_query = str(prompt or "").strip()
        rewrite_needed = bool(payload.get("rewrite_needed"))
        rewrite_needed = rewrite_needed and rewritten_query != str(prompt or "").strip()

        tool_required = bool(payload.get("tool_required"))
        primary_tool = self._normalize_optional_token(payload.get("primary_tool"))
        tool_categories = self._normalize_string_list(
            payload.get("tool_categories")
        )
        allowed_tool_names = self._normalize_string_list(
            payload.get("allowed_tool_names")
        )
        planner_mode = self._normalize_optional_token(
            payload.get("planner_mode")
        )
        if planner_mode not in self.VALID_PLANNER_MODES:
            planner_mode = None
        planner_tool_hints = self._normalize_string_list(
            payload.get("planner_tool_hints")
        )

        document_intent = self._normalize_optional_token(
            payload.get("document_query_intent")
        )
        if document_intent not in self.VALID_DOCUMENT_INTENTS:
            document_intent = None

        document_summary_focus = self._normalize_optional_token(
            payload.get("document_summary_focus")
        )
        if document_summary_focus not in self.VALID_DOCUMENT_SUMMARY_FOCI:
            document_summary_focus = None

        document_answer_mode = self._normalize_optional_token(
            payload.get("document_answer_mode")
        )
        if document_answer_mode not in self.VALID_DOCUMENT_ANSWER_MODES:
            document_answer_mode = None

        rag_file_count = len(getattr(llm_request, "rag_files", []) or [])
        derived_primary_tool = self._derive_document_primary_tool(
            document_intent,
            rag_file_count=rag_file_count,
        )
        derived_answer_mode = self._derive_document_answer_mode(
            document_intent,
        )

        if document_intent and document_answer_mode is None:
            document_answer_mode = derived_answer_mode

        if document_intent and derived_primary_tool and primary_tool is None:
            primary_tool = derived_primary_tool

        if document_intent and primary_tool:
            tool_required = True

        if not tool_required:
            primary_tool = None
            tool_categories = []
            allowed_tool_names = []
            planner_mode = None
            planner_tool_hints = []
        else:
            if primary_tool and not tool_categories:
                tool_categories = self._derive_categories_for_tool(primary_tool)
            tool_categories = self._ensure_primary_tool_categories(
                tool_categories,
                primary_tool,
            )
            if primary_tool and not planner_tool_hints:
                planner_tool_hints = [primary_tool]
            if primary_tool and primary_tool not in allowed_tool_names:
                allowed_tool_names.insert(0, primary_tool)
            if not allowed_tool_names and planner_tool_hints:
                allowed_tool_names = list(planner_tool_hints)
            if planner_mode is None and len(allowed_tool_names) > 1:
                planner_mode = "select_tools"

        answer_strategy = self._normalize_optional_token(
            payload.get("answer_strategy")
        )
        if answer_strategy not in self.VALID_ANSWER_STRATEGIES:
            answer_strategy = self._derive_answer_strategy(
                tool_required=tool_required,
                document_answer_mode=document_answer_mode,
            )

        finalization_mode = self._normalize_optional_token(
            payload.get("finalization_mode")
        )
        if finalization_mode not in self.VALID_FINALIZATION_MODES:
            finalization_mode = self._derive_finalization_mode(
                document_answer_mode=document_answer_mode,
            )

        request_plan = RequestPlan(
            rewrite_needed=rewrite_needed,
            rewritten_query=rewritten_query,
            tool_required=tool_required,
            tool_categories=list(tool_categories),
            allowed_tool_names=list(allowed_tool_names),
            primary_tool=primary_tool,
            planner_mode=planner_mode,
            planner_tool_hints=list(planner_tool_hints),
            document_query_intent=document_intent,
            document_summary_focus=document_summary_focus,
            document_answer_mode=document_answer_mode,
            answer_strategy=answer_strategy,
            finalization_mode=finalization_mode,
        )

        return {
            "rewrite_needed": rewrite_needed,
            "rewritten_query": rewritten_query,
            "tool_required": tool_required,
            "tool_categories": tool_categories,
            "allowed_tool_names": allowed_tool_names,
            "primary_tool": primary_tool,
            "planner_mode": planner_mode,
            "planner_tool_hints": planner_tool_hints,
            "document_query_intent": document_intent,
            "document_summary_focus": document_summary_focus,
            "document_answer_mode": document_answer_mode,
            "answer_strategy": answer_strategy,
            "finalization_mode": finalization_mode,
            "request_plan": request_plan,
        }

    def _preprocess_request(
        self,
        prompt: str,
        *,
        action: Any,
        llm_request: Any,
        conversation: Any = None,
    ) -> Optional[Dict[str, Any]]:
        """Use the active model to analyze, rewrite, and route the prompt."""
        if not str(prompt or "").strip():
            return {
                "rewrite_needed": False,
                "rewritten_query": "",
                "tool_required": False,
                "tool_categories": [],
                "primary_tool": None,
                "planner_tool_hints": [],
                "document_query_intent": None,
                "document_summary_focus": None,
                "document_answer_mode": None,
            }

        prompt_text = self._build_request_preprocess_prompt(
            prompt,
            action=action,
            llm_request=llm_request,
            conversation=conversation,
        )
        try:
            response_text = self._invoke_request_preprocessor(prompt_text)
        except Exception as exc:
            self.logger.warning("Request preprocessing failed: %s", exc)
            return None
        if not response_text:
            return None

        payload = self._extract_json_object(response_text)
        if payload is None:
            self.logger.warning(
                "Request preprocessing returned no JSON payload: %s",
                self._strip_reasoning_markup(response_text)[:300],
            )
            return None
        return self._normalize_preprocess_payload(
            payload,
            prompt=prompt,
            llm_request=llm_request,
        )

    def _classify_prompt_for_tools(self, prompt: str) -> list:
        """Return tool categories from the request preprocessor."""
        result = self._preprocess_request(
            prompt,
            action=None,
            llm_request=getattr(self, "llm_request", None),
            conversation=None,
        )
        if result is None:
            return []
        return list(result.get("tool_categories") or [])

    def _should_use_harness(self, prompt: str) -> bool:
        """Check if a prompt should use the long-running harness."""
        try:
            from airunner.components.llm.long_running import should_use_harness

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