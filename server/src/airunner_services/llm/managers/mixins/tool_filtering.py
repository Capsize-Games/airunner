"""Tool filter application and interruption helpers."""

from __future__ import annotations

from datetime import datetime, timezone
import os
from typing import Any, List, Optional

from airunner_services.contract_enums import LLMActionType
from airunner_services.llm.core.tool_registry import ToolCategory
from airunner_services.llm.managers.tool_selection_plan import (
    ToolSelectionPlan,
)
from airunner_services.llm_workflow_events import (
    resolve_llm_workflow_event_sink,
)


class ToolFilteringMixin:
    """Apply per-request tool filtering to the workflow manager."""

    CATEGORY_ALIASES = {
        "user_data": "knowledge",
        "agent": "system",
        "agents": "system",
        "memory": "knowledge",
    }

    def _build_tool_selection_plan(
        self,
        prompt: str,
        tool_categories: Optional[List[str]],
        action: Any = None,
        force_tool: Optional[str] = None,
        allow_thinking: bool = True,
        request_id: Optional[str] = None,
        auto_select: bool = False,
    ) -> ToolSelectionPlan:
        """Return the canonical tool-selection plan for one request."""
        selected_categories = None
        resolved_force_tool = force_tool
        if auto_select:
            selected_categories, resolved_force_tool = (
                self._auto_select_tool_categories(
                    prompt=prompt,
                    force_tool=force_tool,
                    allow_thinking=allow_thinking,
                    request_id=request_id,
                )
            )
        elif tool_categories is not None:
            selected_categories = list(tool_categories)

        if not self._workflow_manager or not self._tool_manager:
            self.logger.warning(
                "Cannot build tool plan - workflow_manager or tool_manager "
                "not initialized"
            )
            return ToolSelectionPlan(
                selected_categories=selected_categories,
                effective_categories=None,
                filtered_tools=None,
                force_tool=resolved_force_tool,
                keep_existing_tools=True,
            )

        if selected_categories is None:
            return self._build_all_tools_plan(action, resolved_force_tool)
        if len(selected_categories) == 0:
            return self._build_empty_tool_plan(
                prompt,
                resolved_force_tool,
            )

        effective_categories = self._normalize_tool_categories(
            selected_categories
        )
        if not effective_categories:
            self.logger.warning(
                "No valid tool categories specified - leaving tools "
                "unchanged"
            )
            return ToolSelectionPlan(
                selected_categories=selected_categories,
                effective_categories=[],
                filtered_tools=None,
                force_tool=resolved_force_tool,
                keep_existing_tools=True,
            )

        filtered_tools = self._tool_manager.get_tools_by_categories(
            [ToolCategory(category) for category in effective_categories],
            include_deferred=True,
        )
        filtered_tools = self._restrict_to_forced_tool(
            filtered_tools,
            resolved_force_tool,
        )
        return ToolSelectionPlan(
            selected_categories=selected_categories,
            effective_categories=effective_categories,
            filtered_tools=filtered_tools,
            force_tool=resolved_force_tool,
            tool_choice=self._resolve_tool_choice(
                resolved_force_tool,
                action,
                effective_categories,
            ),
        )

    def _auto_select_tool_categories(
        self,
        prompt: str,
        force_tool: Optional[str] = None,
        allow_thinking: bool = True,
        request_id: Optional[str] = None,
    ) -> tuple[list[str], Optional[str]]:
        """Return auto-selected categories and any forced tool override."""
        tool_status_id = (
            f"tool_classification_{request_id}"
            if request_id
            else "tool_classification"
        )
        self._emit_tool_selection_status(
            tool_status_id,
            prompt,
            "starting",
            "Analyzing prompt to select tools...",
            request_id,
        )

        direct_categories, direct_force_tool = self._detect_simple_tool_route(
            prompt
        )
        if force_tool is None and direct_force_tool:
            force_tool = direct_force_tool

        if direct_categories is not None:
            selected_categories = direct_categories
            self.logger.info(
                "Auto mode: matched direct system tool route %s for prompt %r",
                force_tool,
                prompt[:100],
            )
        elif self._is_simple_greeting_prompt(prompt):
            self.logger.info("Auto mode: greeting detected, disabling tools")
            selected_categories = []
        elif self._is_simple_no_tool_prompt(prompt):
            self.logger.info(
                "Auto mode: simple conversational prompt detected, "
                "disabling tools"
            )
            selected_categories = []
        elif self._is_constrained_reply_prompt(prompt):
            self.logger.info(
                "Auto mode: constrained reply prompt detected, "
                "disabling tools"
            )
            selected_categories = []
        elif self._has_search_trigger_prompt(prompt):
            self.logger.info(
                "Auto mode: search intent detected, forcing search category"
            )
            selected_categories = ["search"]
        else:
            selected_categories = self._classify_prompt_for_tools(
                prompt,
                allow_thinking=allow_thinking,
            )

        details = (
            "Selected: "
            f"{', '.join(selected_categories) if selected_categories else 'none'}"
        )
        if force_tool:
            details += f" | forced tool: {force_tool}"
        self._emit_tool_selection_status(
            tool_status_id,
            prompt,
            "completed",
            details,
            request_id,
        )
        return selected_categories, force_tool

    def _emit_tool_selection_status(
        self,
        tool_status_id: str,
        prompt: str,
        status: str,
        details: str,
        request_id: Optional[str],
    ) -> None:
        """Emit one tool-selection status event."""
        event_sink = resolve_llm_workflow_event_sink(self)
        event_sink.emit_tool_status(
            {
                "tool_id": tool_status_id,
                "tool_name": "tool_analyzer",
                "query": prompt[:100],
                "status": status,
                "details": details,
                "conversation_id": getattr(self, "_conversation_id", None),
                "request_id": request_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )

    def _build_all_tools_plan(
        self,
        action: Any,
        force_tool: Optional[str],
    ) -> ToolSelectionPlan:
        """Return the plan that enables the full tool set."""
        self.logger.info("tool_categories=None - enabling all tools")
        return ToolSelectionPlan(
            selected_categories=None,
            effective_categories=None,
            filtered_tools=self._tool_manager.get_all_tools(),
            force_tool=force_tool,
            tool_choice=self._resolve_tool_choice(force_tool, action, None),
            rebuild_workflow=True,
        )

    def _build_empty_tool_plan(
        self,
        prompt: str,
        force_tool: Optional[str],
    ) -> ToolSelectionPlan:
        """Return the plan for an explicit empty category selection."""
        disable_always = (
            os.environ.get("AIRUNNER_DISABLE_ALWAYS_TOOLS", "0") == "1"
        )
        if (
            disable_always
            or self._is_simple_greeting_prompt(prompt)
            or self._is_simple_no_tool_prompt(prompt)
        ):
            self.logger.info(
                "tool_categories=[] - disabling all tools for this request"
            )
            return ToolSelectionPlan(
                selected_categories=[],
                effective_categories=[],
                filtered_tools=[],
                force_tool=force_tool,
                rebuild_workflow=True,
            )

        effective_categories = sorted(self.ALWAYS_INCLUDE_CATEGORIES)
        self.logger.info(
            "tool_categories=[] - including always-available categories: %s",
            effective_categories,
        )
        return ToolSelectionPlan(
            selected_categories=[],
            effective_categories=effective_categories,
            filtered_tools=self._tool_manager.get_tools_by_categories(
                [ToolCategory(category) for category in effective_categories],
                include_deferred=False,
            ),
            force_tool=force_tool,
            rebuild_workflow=True,
        )

    def _normalize_tool_categories(
        self,
        tool_categories: List[str],
    ) -> list[str]:
        """Normalize aliases and add always-include categories."""
        effective_categories: list[str] = []
        seen_categories: set[str] = set()
        for cat_name in tool_categories:
            category_name = self.CATEGORY_ALIASES.get(
                (cat_name or "").lower(),
                (cat_name or "").lower(),
            )
            try:
                category = ToolCategory(category_name)
            except ValueError:
                self.logger.warning(
                    "Unknown tool category: %s. Valid categories: %s. "
                    "Valid aliases: %s",
                    cat_name,
                    [item.value for item in ToolCategory],
                    sorted(self.CATEGORY_ALIASES),
                )
                continue
            if category.value not in seen_categories:
                effective_categories.append(category.value)
                seen_categories.add(category.value)

        for always_cat in sorted(self.ALWAYS_INCLUDE_CATEGORIES):
            if always_cat not in seen_categories:
                effective_categories.append(always_cat)
                seen_categories.add(always_cat)
        return effective_categories

    def _restrict_to_forced_tool(
        self,
        filtered_tools: list[Any],
        force_tool: Optional[str],
    ) -> list[Any]:
        """Reduce the filtered tool set to one forced tool when requested."""
        if not force_tool:
            return filtered_tools

        forced_tools = [
            tool
            for tool in filtered_tools
            if getattr(tool, "name", getattr(tool, "__name__", None))
            == force_tool
        ]
        if forced_tools:
            self.logger.info(
                "[TOOL FILTER] Reduced filtered tools to forced tool: %s",
                force_tool,
            )
            return forced_tools

        self.logger.warning(
            "[TOOL FILTER] Forced tool '%s' was not found in filtered tool "
            "set",
            force_tool,
        )
        return filtered_tools

    def _resolve_tool_choice(
        self,
        force_tool: Optional[str],
        action: Any,
        tool_categories: Optional[List[str]],
    ) -> Any:
        """Return the request-time tool choice override."""
        supports_forced_choice = bool(
            getattr(self, "supports_function_calling", False)
        )
        if force_tool:
            self.logger.info("[TOOL FILTER] Forcing tool: %s", force_tool)
            return {
                "type": "function",
                "function": {"name": force_tool},
            }
        if (
            supports_forced_choice
            and action == LLMActionType.PERFORM_RAG_SEARCH
        ):
            return "any"
        if (
            supports_forced_choice
            and tool_categories
            and ("search" in tool_categories or "research" in tool_categories)
        ):
            return "any"
        if action == LLMActionType.CODE:
            self.logger.info(
                "[TOOL FILTER] CODE action uses generic fallback handling; "
                "leaving tool_choice unset"
            )
        return None

    def _apply_tool_selection_plan(
        self,
        plan: ToolSelectionPlan,
    ) -> None:
        """Apply a prepared tool-selection plan to the workflow manager."""
        if not self._workflow_manager:
            return
        if plan.keep_existing_tools or plan.filtered_tools is None:
            self.logger.info(
                "[TOOL FILTER] Leaving existing workflow tools unchanged"
            )
            return

        filtered_names = [
            getattr(tool, "name", getattr(tool, "__name__", str(tool)))
            for tool in plan.filtered_tools
        ]
        self.logger.info(
            "[TOOL FILTER] Applying plan categories=%s effective=%s tools=%s",
            plan.selected_categories,
            plan.effective_categories,
            filtered_names,
        )

        update_kwargs = {}
        if plan.tool_choice is not None:
            update_kwargs["tool_choice"] = plan.tool_choice
        self._workflow_manager.update_tools(
            plan.filtered_tools, **update_kwargs
        )
        if plan.rebuild_workflow:
            self._workflow_manager._build_and_compile_workflow()

    def _apply_tool_filter(
        self,
        tool_categories: List[str],
        action=None,
        force_tool: Optional[str] = None,
    ) -> None:
        """Apply a tool category filter to the active workflow."""
        plan = self._build_tool_selection_plan(
            prompt=getattr(getattr(self, "llm_request", None), "prompt", ""),
            tool_categories=tool_categories,
            action=action,
            force_tool=force_tool,
        )
        self._apply_tool_selection_plan(plan)

    def _restore_all_tools(self) -> None:
        """Restore all tools to the workflow after a filtered request."""
        if self._workflow_manager and self._tool_manager:
            all_tools = self._tool_manager.get_all_tools()
            self._workflow_manager.update_tools(all_tools)

    def do_interrupt(self) -> None:
        """Interrupt ongoing generation."""
        self.logger.info("do_interrupt called on instance %s", id(self))
        self._interrupted = True

        if self._chat_model and hasattr(self._chat_model, "set_interrupted"):
            self.logger.info(
                "Setting interrupt on chat_model %s",
                id(self._chat_model),
            )
            self._chat_model.set_interrupted(True)
        else:
            self.logger.warning(
                "Chat model not available or missing set_interrupted: %s",
                self._chat_model,
            )

        if self._workflow_manager and hasattr(
            self._workflow_manager,
            "set_interrupted",
        ):
            self.logger.info(
                "Setting interrupt on workflow_manager %s",
                id(self._workflow_manager),
            )
            self._workflow_manager.set_interrupted(True)
        else:
            self.logger.warning(
                "Workflow manager not available: %s",
                self._workflow_manager,
            )

    def on_section_changed(self) -> None:
        """Handle section change events."""
        self.logger.info("Section changed, clearing history")
        self.clear_history()
