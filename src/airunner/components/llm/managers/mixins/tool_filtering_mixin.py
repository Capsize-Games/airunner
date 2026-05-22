"""Tool filter application and interruption helpers."""

from __future__ import annotations

import os
from typing import List, Optional

from airunner.enums import LLMActionType


class ToolFilteringMixin:
    """Apply per-request tool filtering to the workflow manager."""

    def _apply_tool_filter(
        self,
        tool_categories: List[str],
        action=None,
        force_tool: Optional[str] = None,
        allowed_tool_names: Optional[List[str]] = None,
    ) -> None:
        """Apply a tool category filter to the active workflow."""
        self.logger.info(
            "[TOOL FILTER] ENTER _apply_tool_filter with categories: %s",
            tool_categories,
        )
        if not self._workflow_manager or not self._tool_manager:
            self.logger.warning(
                "Cannot apply tool filter - workflow_manager or tool_manager "
                "not initialized"
            )
            self.logger.info(
                "[TOOL FILTER] workflow_manager: %s, tool_manager: %s",
                self._workflow_manager,
                self._tool_manager,
            )
            return

        from airunner.components.llm.core.tool_registry import ToolCategory

        if tool_categories is not None and len(tool_categories) == 0:
            self.logger.info("tool_categories=[] - disabling all tools")
            self._workflow_manager.update_tools([])
            self._workflow_manager._build_and_compile_workflow()
            return

        if tool_categories is None:
            self.logger.info(
                "tool_categories=None - enabling all tools for this request"
            )
            all_tools = self._tool_manager.get_all_tools()
            self._workflow_manager.update_tools(all_tools)
            self._workflow_manager._build_and_compile_workflow()
            self.logger.info(
                "All tools enabled successfully - workflow rebuilt with %s "
                "tools",
                len(all_tools),
            )
            return

        category_aliases = {
            "user_data": "knowledge",
            "agent": "system",
            "agents": "system",
            "memory": "knowledge",
        }
        allowed_categories = set()
        for cat_name in tool_categories:
            cat_lower = cat_name.lower()
            if cat_lower in category_aliases:
                actual_cat = category_aliases[cat_lower]
                self.logger.info(
                    "Mapped alias '%s' to category '%s'",
                    cat_name,
                    actual_cat,
                )
                cat_lower = actual_cat

            try:
                category = ToolCategory(cat_lower)
                allowed_categories.add(category)
                self.logger.info("Added category: %s", category.value)
            except ValueError:
                self.logger.warning(
                    "Unknown tool category: %s. Valid categories: %s. "
                    "Valid aliases: %s",
                    cat_name,
                    [c.value for c in ToolCategory],
                    list(category_aliases.keys()),
                )

        self.logger.info(
            "[TOOL FILTER DEBUG] allowed_categories computed: %s",
            [category.value for category in allowed_categories],
        )
        if not allowed_categories:
            self.logger.warning(
                "No valid tool categories specified - using all tools"
            )
            return

        for always_cat in self.ALWAYS_INCLUDE_CATEGORIES:
            try:
                category = ToolCategory(always_cat)
                if category not in allowed_categories:
                    allowed_categories.add(category)
                    self.logger.info(
                        "Added always-include category: %s",
                        category.value,
                    )
            except ValueError:
                continue

        self.logger.info(
            "[TOOL FILTER] Getting tools by categories: %s",
            list(allowed_categories),
        )
        filtered_tools = self._tool_manager.get_tools_by_categories(
            list(allowed_categories),
            include_deferred=True,
        )
        if allowed_tool_names:
            allowed_names = set(allowed_tool_names)
            filtered_tools = [
                tool
                for tool in filtered_tools
                if getattr(tool, "name", getattr(tool, "__name__", None))
                in allowed_names
            ]
            self.logger.info(
                "[TOOL FILTER] Restricted filtered tools to allowlist: %s",
                sorted(allowed_names),
            )
        if force_tool:
            forced_tools = [
                tool
                for tool in filtered_tools
                if getattr(tool, "name", getattr(tool, "__name__", None))
                == force_tool
            ]
            if forced_tools:
                filtered_tools = forced_tools
                self.logger.info(
                    "[TOOL FILTER] Reduced filtered tools to forced tool: %s",
                    force_tool,
                )
            else:
                self.logger.warning(
                    "[TOOL FILTER] Forced tool '%s' was not found in filtered "
                    "tool set",
                    force_tool,
                )

        try:
            filtered_names = [
                getattr(tool, "name", getattr(tool, "__name__", str(tool)))
                for tool in filtered_tools
            ]
        except Exception:
            filtered_names = str(filtered_tools)

        self.logger.info(
            "[TOOL FILTER DEBUG] Filtered tools: %s",
            filtered_names,
        )
        self.logger.info(
            "[TOOL FILTER] Got %s filtered tools",
            len(filtered_tools),
        )
        self.logger.info(
            "Filtered to %s tools from categories: %s",
            len(filtered_tools),
            tool_categories,
        )
        self.logger.info(
            "[TOOL FILTER] Calling update_tools with %s tools",
            len(filtered_tools),
        )

        tool_choice = None
        supports_forced_choice = bool(
            getattr(self, "supports_function_calling", False)
        )
        planner_requires_tool = bool(
            supports_forced_choice
            and allowed_tool_names
            and getattr(
                getattr(self, "llm_request", None),
                "planner_mode",
                None,
            )
            == "select_tools"
        )
        if force_tool:
            tool_choice = {
                "type": "function",
                "function": {"name": force_tool},
            }
            self.logger.info("[TOOL FILTER] Forcing tool: %s", force_tool)
        elif planner_requires_tool:
            tool_choice = "any"
            self.logger.info(
                "[TOOL FILTER] Planner mode requires a tool call from the "
                "restricted allowlist"
            )
        elif (
            supports_forced_choice
            and action == LLMActionType.PERFORM_RAG_SEARCH
        ):
            tool_choice = "any"
        elif supports_forced_choice and tool_categories and (
            "search" in tool_categories or "research" in tool_categories
        ):
            tool_choice = "any"
        elif action == LLMActionType.CODE:
            self.logger.info(
                "[TOOL FILTER] CODE action uses generic fallback handling; "
                "leaving tool_choice unset"
            )

        self._workflow_manager.update_tools(
            filtered_tools,
            tool_choice=tool_choice,
        )

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