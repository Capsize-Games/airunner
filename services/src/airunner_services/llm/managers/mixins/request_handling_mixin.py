"""Request orchestration for LLM generation."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from airunner_services.database.models.llm_generator_settings import (
    LLMGeneratorSettings,
)
from airunner_services.llm.managers.request_preparation import (
    capture_request_settings_snapshot,
    extract_request_tool_defaults,
    normalize_requested_dtype,
    normalize_requested_service,
    restore_request_settings_snapshot,
)
from airunner_services.llm.managers.request_rag_preparation import (
    ensure_request_rag_files,
    load_rag_document_payload,
    prepare_request_rag,
)
from airunner_services.llm_workflow_events import (
    resolve_llm_workflow_event_sink,
)


class RequestHandlingMixin:
    """Coordinate request-time model, tool, and RAG preparation."""

    def handle_request(
        self,
        data: Dict,
        extra_context: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Handle an incoming request for LLM generation."""
        self.logger.info("handle_request called on instance %s", id(self))
        self._invalidate_setting_cache(LLMGeneratorSettings)

        self._current_request_id = data.get("request_id")
        if not self._current_request_id:
            self.logger.warning(
                "[REQUEST] Missing request_id on incoming request; "
                "streaming responses will not be routed"
            )
        else:
            self.logger.debug(
                "[REQUEST] Set _current_request_id=%s",
                self._current_request_id,
            )

        self._interrupted = False
        if self._chat_model and hasattr(self._chat_model, "set_interrupted"):
            self._chat_model.set_interrupted(False)
        if self._workflow_manager and hasattr(
            self._workflow_manager,
            "set_interrupted",
        ):
            self._workflow_manager.set_interrupted(False)

        llm_request = data["request_data"].get("llm_request")
        self.llm_request = llm_request
        if llm_request is not None:
            try:
                setattr(
                    llm_request,
                    "prompt",
                    data["request_data"].get("prompt", ""),
                )
            except Exception:
                pass

        settings_snapshot = capture_request_settings_snapshot(self)
        request_settings_changed = self._apply_request_overrides(
            llm_request
        )
        if request_settings_changed:
            self.unload()

        self._do_set_seed()
        self.load()

        request_tool_defaults = self._request_tool_defaults(data)

        self._prepare_request_memory(llm_request)
        self._prepare_request_conversation(data, llm_request)

        tools_filtered, selected_categories, system_prompt = (
            self._prepare_request_tooling(data, llm_request)
        )
        self._prepare_request_rag(data, llm_request, selected_categories)
        thinking_patches = self._apply_request_thinking_override(llm_request)
        reasoning_patches = self._apply_request_reasoning_effort_override(
            llm_request
        )

        if request_tool_defaults and self._tool_manager:
            self._tool_manager.set_request_tool_defaults(request_tool_defaults)

        try:
            return self._do_generate(
                prompt=data["request_data"]["prompt"],
                action=data["request_data"]["action"],
                system_prompt=system_prompt,
                llm_request=data["request_data"]["llm_request"],
                extra_context=extra_context,
                skip_tool_setup=tools_filtered,
            )
        finally:
            self._restore_thinking_patches(thinking_patches)
            self._restore_reasoning_effort_patches(reasoning_patches)
            if request_tool_defaults and self._tool_manager:
                self._tool_manager.clear_request_tool_defaults()
            if request_settings_changed:
                restore_request_settings_snapshot(
                    self,
                    settings_snapshot,
                )
                self.unload()

    def _requested_service(self, llm_request: Any) -> Optional[str]:
        """Return the requested service override, if any."""
        return normalize_requested_service(
            getattr(llm_request, "model_service", None)
        )

    def _apply_request_overrides(self, llm_request: Any) -> bool:
        """Apply request-scoped settings overrides and report changes."""
        settings_changed = False
        desired_dtype = normalize_requested_dtype(
            getattr(llm_request, "dtype", None)
        )
        if desired_dtype:
            settings_changed = self._apply_requested_dtype(desired_dtype)

        desired_service = self._requested_service(llm_request)
        if desired_service:
            settings_changed = (
                self._apply_requested_service(desired_service, llm_request)
                or settings_changed
            )

        return settings_changed

    def _apply_requested_dtype(self, desired_dtype: str) -> bool:
        """Apply one request-scoped dtype override when it changes."""
        current_dtype = normalize_requested_dtype(
            getattr(self.llm_generator_settings, "dtype", None)
        )
        if current_dtype == desired_dtype:
            return False

        self.logger.info(
            "[LLM] Switching dtype %s -> %s for request",
            current_dtype,
            desired_dtype,
        )
        self.llm_generator_settings.dtype = desired_dtype
        return True

    def _prepare_request_memory(self, llm_request: Any) -> None:
        """Reset workflow memory when the request disables memory usage."""
        if not llm_request or getattr(llm_request, "use_memory", True):
            return

        self.logger.info(
            "use_memory=False - clearing conversation history for this "
            "request"
        )
        if self._workflow_manager:
            self._workflow_manager.clear_memory()

    def _prepare_request_conversation(
        self,
        data: Dict[str, Any],
        llm_request: Any,
    ) -> None:
        """Attach the request to the active conversation workflow state."""
        conversation = self._get_or_create_conversation(data)
        if not conversation:
            return

        ephemeral = bool(
            getattr(llm_request, "ephemeral_conversation", False)
        )
        if hasattr(self, "_update_workflow_with_conversation"):
            self._update_workflow_with_conversation(
                conversation,
                ephemeral=ephemeral,
            )
            return

        if self._workflow_manager:
            self._workflow_manager.set_conversation_id(
                conversation.id,
                ephemeral=ephemeral,
            )

    def _current_service(self) -> str:
        """Return the currently active LLM provider kind."""
        if getattr(self.llm_settings, "use_openrouter", False):
            return "openrouter"
        if getattr(self.llm_settings, "use_ollama", False):
            return "ollama"
        return "local"

    def _apply_requested_service(
        self,
        desired_service: str,
        llm_request: Any,
    ) -> bool:
        """Apply provider flags and request-level model overrides."""
        current_service = self._current_service()
        settings_changed = current_service != desired_service
        if current_service != desired_service:
            self.logger.info(
                "[LLM] Switching model_service %s -> %s for request",
                current_service,
                desired_service,
            )

        self.llm_settings.use_openrouter = desired_service == "openrouter"
        self.llm_settings.use_ollama = desired_service == "ollama"
        self.llm_settings.use_local_llm = desired_service == "local"

        api_model = getattr(llm_request, "api_model", None)
        if isinstance(api_model, str) and api_model.strip():
            api_model = api_model.strip()
            if desired_service == "openrouter":
                if getattr(self.llm_settings, "model", None) != api_model:
                    self.llm_settings.model = api_model
                    settings_changed = True
            elif desired_service == "ollama":
                if (
                    getattr(self.llm_settings, "ollama_model", None)
                    != api_model
                ):
                    self.llm_settings.ollama_model = api_model
                    settings_changed = True

        return settings_changed

    def _request_tool_defaults(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Build default tool arguments from request search hints."""
        request_data = data.get("request_data", {})
        if not isinstance(request_data, dict):
            return {}
        return extract_request_tool_defaults(request_data)

    def _prepare_request_tooling(
        self,
        data: Dict[str, Any],
        llm_request: Any,
    ) -> tuple[bool, List[str], Optional[str]]:
        """Apply per-request tool filtering and system prompt overrides."""
        tools_filtered = False
        selected_categories: List[str] = []
        system_prompt = None
        if llm_request:
            self.logger.info(
                "[LLM MANAGER DEBUG] llm_request.tool_categories=%s",
                llm_request.tool_categories,
            )
            if getattr(llm_request, "system_prompt", None):
                system_prompt = llm_request.system_prompt
                self.logger.info(
                    "Using custom system prompt from request: %s...",
                    system_prompt[:100],
                )

        prompt = data["request_data"]["prompt"]
        action = data["request_data"].get("action")

        if llm_request and llm_request.tool_categories is None:
            selected_categories = self._auto_select_tool_categories(
                llm_request,
                prompt,
            )
            self._apply_tool_filter(
                selected_categories,
                action=action,
                force_tool=getattr(llm_request, "force_tool", None),
            )
            tools_filtered = True
        elif llm_request and llm_request.tool_categories is not None:
            self.logger.info(
                "[LLM MANAGER DEBUG] APPLYING TOOL FILTER with %s",
                llm_request.tool_categories,
            )
            self.logger.info(
                "Applying tool filter with categories: %s",
                llm_request.tool_categories,
            )
            self._apply_tool_filter(
                llm_request.tool_categories,
                action=action,
                force_tool=getattr(llm_request, "force_tool", None),
            )
            selected_categories = list(llm_request.tool_categories)
            tools_filtered = True
        else:
            self.logger.info(
                "[LLM MANAGER DEBUG] NOT APPLYING FILTER - tool_categories "
                "is None"
            )
            self.logger.info("No tool filtering - using all tools")

        return tools_filtered, selected_categories, system_prompt

    def _auto_select_tool_categories(
        self,
        llm_request: Any,
        prompt: str,
    ) -> List[str]:
        """Classify tool categories and emit UI status updates."""
        request_id = getattr(self, "_current_request_id", None)
        tool_status_id = (
            f"tool_classification_{request_id}"
            if request_id
            else "tool_classification"
        )
        self.logger.info(
            "Auto mode: Analyzing prompt to select relevant tool categories"
        )
        event_sink = resolve_llm_workflow_event_sink(self)
        force_tool = getattr(llm_request, "force_tool", None)
        direct_categories, direct_force_tool = self._detect_simple_tool_route(
            prompt
        )
        if force_tool is None and direct_force_tool:
            force_tool = direct_force_tool

        event_sink.emit_tool_status(
            {
                "tool_id": tool_status_id,
                "tool_name": "tool_analyzer",
                "query": prompt[:100],
                "status": "starting",
                "details": "Analyzing prompt to select tools...",
                "conversation_id": getattr(self, "_conversation_id", None),
                "request_id": request_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )

        if direct_categories is not None:
            selected_categories = direct_categories
            self.logger.info(
                "Auto mode: matched direct system tool route %s for prompt %r",
                force_tool,
                prompt[:100],
            )
        else:
            allow_thinking = getattr(llm_request, "enable_thinking", None)
            if allow_thinking is None:
                allow_thinking = True
            selected_categories = self._classify_prompt_for_tools(
                prompt,
                allow_thinking=allow_thinking,
            )

        llm_request.tool_categories = selected_categories
        llm_request.force_tool = force_tool

        details = (
            "Selected: "
            f"{', '.join(selected_categories) if selected_categories else 'none'}"
        )
        if force_tool:
            details += f" | forced tool: {force_tool}"
        event_sink.emit_tool_status(
            {
                "tool_id": tool_status_id,
                "tool_name": "tool_analyzer",
                "query": prompt[:100],
                "status": "completed",
                "details": details,
                "conversation_id": getattr(self, "_conversation_id", None),
                "request_id": request_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )
        self.logger.info(
            "Auto mode selected categories: %s",
            selected_categories,
        )
        return selected_categories

    def _prepare_request_rag(
        self,
        data: Dict[str, Any],
        llm_request: Any,
        selected_categories: List[str],
    ) -> None:
        """Ensure request-provided or inferred RAG files are indexed."""
        del data
        prepare_request_rag(self, llm_request, selected_categories)

    def _ensure_request_rag_files(self, rag_files: Any) -> None:
        """Load and index request-provided RAG files."""
        ensure_request_rag_files(self, rag_files)

    def _load_rag_document_payload(self, doc: Dict[str, Any]) -> None:
        """Load one request-provided document payload into RAG."""
        load_rag_document_payload(self, doc)

    def _apply_request_thinking_override(
        self,
        llm_request: Any,
    ) -> list[tuple[Any, Any]]:
        """Patch thinking flags on active chat models for one request."""
        thinking_override = getattr(llm_request, "enable_thinking", None)
        thinking_patches: list[tuple[Any, Any]] = []
        if thinking_override is None:
            return thinking_patches

        targets = [self._chat_model]
        if self._workflow_manager:
            targets.append(
                getattr(self._workflow_manager, "_original_chat_model", None)
            )

        for target in targets:
            if target is None or not hasattr(target, "enable_thinking"):
                continue
            try:
                thinking_patches.append(
                    (target, getattr(target, "enable_thinking"))
                )
                setattr(target, "enable_thinking", bool(thinking_override))
            except Exception:
                continue
        return thinking_patches

    def _restore_thinking_patches(
        self,
        thinking_patches: list[tuple[Any, Any]],
    ) -> None:
        """Restore chat-model thinking flags after request completion."""
        for target, original in thinking_patches:
            try:
                setattr(target, "enable_thinking", original)
            except Exception:
                continue

    def _apply_request_reasoning_effort_override(
        self,
        llm_request: Any,
    ) -> list[tuple[Any, Any]]:
        """Patch GPT-OSS reasoning effort on active chat models for one request."""
        reasoning_effort = getattr(llm_request, "reasoning_effort", None)
        if isinstance(reasoning_effort, str):
            reasoning_effort = reasoning_effort.strip().lower() or None
        if reasoning_effort not in {"low", "medium", "high"}:
            return []

        reasoning_patches: list[tuple[Any, Any]] = []
        targets = [self._chat_model]
        if self._workflow_manager:
            targets.append(
                getattr(self._workflow_manager, "_original_chat_model", None)
            )

        for target in targets:
            if target is None or not hasattr(target, "reasoning_effort"):
                continue
            try:
                reasoning_patches.append(
                    (target, getattr(target, "reasoning_effort"))
                )
                setattr(target, "reasoning_effort", reasoning_effort)
            except Exception:
                continue

        return reasoning_patches

    def _restore_reasoning_effort_patches(
        self,
        reasoning_patches: list[tuple[Any, Any]],
    ) -> None:
        """Restore chat-model GPT-OSS reasoning effort after request completion."""
        for target, original in reasoning_patches:
            try:
                setattr(target, "reasoning_effort", original)
            except Exception:
                continue