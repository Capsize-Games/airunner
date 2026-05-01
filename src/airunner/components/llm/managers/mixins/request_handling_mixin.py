"""Request orchestration for LLM generation."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from airunner.components.data.session_manager import session_scope
from airunner.components.documents.data.models.document import Document
from airunner.enums import SignalCode


class RequestHandlingMixin:
    """Coordinate request-time model, tool, and RAG preparation."""

    def handle_request(
        self,
        data: Dict,
        extra_context: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Handle an incoming request for LLM generation."""
        self.logger.info("handle_request called on instance %s", id(self))

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

        desired_dtype = getattr(llm_request, "dtype", None)
        if isinstance(desired_dtype, str):
            desired_dtype = desired_dtype.strip().lower() or None
        if desired_dtype in ("4-bit", "4bit"):
            desired_dtype = "4bit"
        elif desired_dtype in ("8-bit", "8bit"):
            desired_dtype = "8bit"
        elif desired_dtype in ("32-bit", "32bit"):
            desired_dtype = "32bit"
        elif desired_dtype != "auto":
            desired_dtype = None

        if desired_dtype:
            current_dtype = getattr(self.llm_generator_settings, "dtype", None)
            if isinstance(current_dtype, str):
                current_dtype = current_dtype.strip().lower() or None
            if current_dtype != desired_dtype:
                self.logger.info(
                    "[LLM] Switching dtype %s -> %s; unloading",
                    current_dtype,
                    desired_dtype,
                )
                self.unload()
                self.llm_generator_settings.dtype = desired_dtype

        desired_service = self._requested_service(llm_request)
        if desired_service:
            self._apply_requested_service(desired_service, llm_request)

        self._do_set_seed()
        self.load()

        request_tool_defaults = self._request_tool_defaults(data)
        self._refresh_workflow_manager_for_mode_request(llm_request)

        if llm_request and not llm_request.use_memory:
            self.logger.info(
                "use_memory=False - clearing conversation history for this "
                "request"
            )
            if self._workflow_manager:
                self._workflow_manager.clear_memory()

        conversation = self._get_or_create_conversation(data)
        if conversation and self._workflow_manager:
            self._workflow_manager.set_conversation_id(
                conversation.id,
                ephemeral=llm_request.ephemeral_conversation,
            )

        tools_filtered, selected_categories, system_prompt = (
            self._prepare_request_tooling(data, llm_request)
        )
        self._prepare_request_rag(data, llm_request, selected_categories)
        thinking_patches = self._apply_request_thinking_override(llm_request)

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
            if request_tool_defaults and self._tool_manager:
                self._tool_manager.clear_request_tool_defaults()

    def _requested_service(self, llm_request: Any) -> Optional[str]:
        """Return the requested service override, if any."""
        desired_service = getattr(llm_request, "model_service", None)
        if isinstance(desired_service, str):
            desired_service = desired_service.strip().lower() or None
        if desired_service not in ("local", "openrouter", "ollama"):
            return None
        return desired_service

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
    ) -> None:
        """Apply provider flags and request-level model overrides."""
        current_service = self._current_service()
        if current_service != desired_service:
            self.logger.info(
                "[LLM] Switching model_service %s -> %s; unloading",
                current_service,
                desired_service,
            )
            self.unload()

        self.llm_settings.use_openrouter = desired_service == "openrouter"
        self.llm_settings.use_ollama = desired_service == "ollama"
        self.llm_settings.use_local_llm = desired_service == "local"

        api_model = getattr(llm_request, "api_model", None)
        if isinstance(api_model, str) and api_model.strip():
            api_model = api_model.strip()
            if desired_service == "openrouter":
                self.llm_settings.model = api_model
            elif desired_service == "ollama":
                self.llm_settings.ollama_model = api_model

    def _request_tool_defaults(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Build default tool arguments from request search hints."""
        defaults: Dict[str, Any] = {}
        search_hints = data.get("request_data", {}).get("search_hints")
        if not isinstance(search_hints, dict):
            return defaults

        locale = search_hints.get("locale")
        if not isinstance(locale, dict):
            return defaults

        country = locale.get("country")
        if isinstance(country, str) and country.strip():
            defaults["country"] = country.strip()
        language = locale.get("language")
        if isinstance(language, str) and language.strip():
            defaults["language"] = language.strip()
        return defaults

    def _refresh_workflow_manager_for_mode_request(
        self,
        llm_request: Any,
    ) -> None:
        """Rebuild the workflow manager when mode-routing settings change."""
        if not llm_request:
            return
        if not (
            getattr(llm_request, "use_mode_routing", False)
            or getattr(llm_request, "mode_override", None)
        ):
            return

        use_mode_routing = getattr(llm_request, "use_mode_routing", False)
        mode_override = getattr(llm_request, "mode_override", None)
        needs_rebuild = self._workflow_manager is None
        if self._workflow_manager:
            current_mode_routing = getattr(
                self._workflow_manager,
                "_use_mode_routing",
                False,
            )
            current_mode_override = getattr(
                self._workflow_manager,
                "_mode_override",
                None,
            )
            if (
                current_mode_routing != use_mode_routing
                or current_mode_override != mode_override
            ):
                needs_rebuild = True
                self.logger.info(
                    "Mode routing settings changed: use_mode_routing=%s, "
                    "mode_override=%s - rebuilding workflow manager",
                    use_mode_routing,
                    mode_override,
                )

        if needs_rebuild:
            self._unload_workflow_manager()
            self._load_workflow_manager()

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
        force_tool = getattr(llm_request, "force_tool", None)
        direct_categories, direct_force_tool = self._detect_simple_tool_route(
            prompt
        )
        if force_tool is None and direct_force_tool:
            force_tool = direct_force_tool

        self.emit_signal(
            SignalCode.LLM_TOOL_STATUS_SIGNAL,
            {
                "tool_id": tool_status_id,
                "tool_name": "tool_analyzer",
                "query": prompt[:100],
                "status": "starting",
                "details": "Analyzing prompt to select tools...",
                "conversation_id": getattr(self, "_conversation_id", None),
                "request_id": request_id,
                "timestamp": datetime.utcnow().isoformat(),
            },
        )

        if direct_categories is not None:
            selected_categories = direct_categories
            self.logger.info(
                "Auto mode: matched direct system tool route %s for prompt %r",
                force_tool,
                prompt[:100],
            )
        else:
            selected_categories = self._classify_prompt_for_tools(prompt)

        llm_request.tool_categories = selected_categories
        llm_request.force_tool = force_tool

        details = (
            "Selected: "
            f"{', '.join(selected_categories) if selected_categories else 'none'}"
        )
        if force_tool:
            details += f" | forced tool: {force_tool}"
        self.emit_signal(
            SignalCode.LLM_TOOL_STATUS_SIGNAL,
            {
                "tool_id": tool_status_id,
                "tool_name": "tool_analyzer",
                "query": prompt[:100],
                "status": "completed",
                "details": details,
                "conversation_id": getattr(self, "_conversation_id", None),
                "request_id": request_id,
                "timestamp": datetime.utcnow().isoformat(),
            },
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
        if llm_request and getattr(llm_request, "rag_files", None):
            self._ensure_request_rag_files(llm_request.rag_files)

        try:
            if llm_request and not getattr(llm_request, "rag_files", None):
                if "search" in (selected_categories or []) and hasattr(
                    self,
                    "ensure_indexed_files",
                ):
                    with session_scope() as session:
                        docs = (
                            session.query(Document)
                            .filter_by(active=True, indexed=True)
                            .all()
                        )
                    if docs:
                        candidates = [doc.path for doc in docs[:3]]
                        llm_request.rag_files = candidates
                        self.logger.info(
                            "Auto-attached %s indexed document(s) to rag_files "
                            "for search: %s",
                            len(candidates),
                            candidates,
                        )
                        self.ensure_indexed_files(candidates)
        except Exception:
            self.logger.debug(
                "Auto attachment of RAG files failed, continuing without "
                "local RAG."
            )

    def _ensure_request_rag_files(self, rag_files: Any) -> None:
        """Load and index request-provided RAG files."""
        try:
            if hasattr(self, "ensure_indexed_files"):
                self.ensure_indexed_files(rag_files)
                return

            for doc in rag_files:
                if isinstance(doc, str):
                    self.load_file_into_rag(doc)
                elif isinstance(doc, (bytes, bytearray)):
                    self.load_bytes_into_rag(doc, source_name="upload")
                elif isinstance(doc, dict) and doc.get("content"):
                    self._load_rag_document_payload(doc)
        except Exception as exc:
            self.logger.warning(
                "Error ensuring rag files are indexed: %s",
                exc,
            )

    def _load_rag_document_payload(self, doc: Dict[str, Any]) -> None:
        """Load one request-provided document payload into RAG."""
        file_type = str(doc.get("file_type", "")).lower()
        content = doc.get("content")
        source_name = doc.get("source_name", "web_content")
        if file_type in [".epub", ".pdf"]:
            payload = content
            if not isinstance(payload, (bytes, bytearray)):
                payload = str(payload).encode("utf-8")
            self.load_bytes_into_rag(
                payload,
                source_name=doc.get("source_name", "upload"),
                file_ext=file_type,
            )
            return

        self.load_html_into_rag(
            str(content),
            source_name=source_name,
        )

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