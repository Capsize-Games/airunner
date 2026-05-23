"""Request orchestration for LLM generation."""

from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace
from typing import Any, Dict, List, Optional

from airunner_model.session import session_scope
from airunner_model.models.document import Document
from airunner.components.llm.managers.request_plan import RequestPlan
from airunner.enums import LLMActionType, SignalCode


class RequestHandlingMixin:
    """Coordinate request-time model, tool, and RAG preparation."""

    DOCUMENT_TOOL_NAMES = {
        "inspect_loaded_documents",
        "analyze_loaded_document",
        "rag_search",
    }

    @staticmethod
    def _request_debug_metadata(llm_request: Any) -> Optional[Dict[str, Any]]:
        """Return one compact request settings snapshot for status UI."""
        build_metadata = getattr(llm_request, "to_debug_metadata", None)
        if not callable(build_metadata):
            return None
        return build_metadata(title="Request Settings")

    @staticmethod
    def _planner_controls_document_tools(llm_request: Any) -> bool:
        """Return whether planner mode should choose document tools."""
        return getattr(llm_request, "planner_mode", None) == "select_tools"

    @staticmethod
    def _coerce_request_plan(result: Any) -> Optional[RequestPlan]:
        """Return one request plan from a preprocess result mapping."""
        if not isinstance(result, dict):
            return None
        request_plan = result.get("request_plan")
        if isinstance(request_plan, RequestPlan):
            return request_plan
        return RequestPlan.from_mapping(result)

    @staticmethod
    def _planner_tool_hints(route: Any) -> List[str]:
        """Return planner-facing tool hints derived from the route."""
        if route is None or not getattr(route, "force_tool", None):
            return []
        if (
            getattr(route, "force_tool", None) == "rag_search"
            and getattr(route, "answer_mode", None) == "synthesized"
        ):
            return ["analyze_loaded_document", "rag_search"]
        return [route.force_tool]

    @classmethod
    def _document_planner_allowed_tool_names(
        cls,
        llm_request: Any,
    ) -> Optional[List[str]]:
        """Return the planner-visible tool surface for attached docs."""
        if not llm_request or not cls._planner_controls_document_tools(
            llm_request
        ):
            return None
        if not getattr(llm_request, "rag_files", None):
            return None
        request_plan = getattr(llm_request, "request_plan", None)
        if request_plan is not None:
            allowed_tool_names = list(
                getattr(request_plan, "allowed_tool_names", []) or []
            )
            if allowed_tool_names:
                return allowed_tool_names
        return [
            "inspect_loaded_documents",
            "analyze_loaded_document",
            "rag_search",
        ]

    @staticmethod
    def _should_auto_activate_document_planner(
        llm_request: Any,
        action: Any,
        requested_force_tool: Optional[str] = None,
    ) -> bool:
        """Return whether chat-with-documents should use planner mode."""
        if not llm_request or action != LLMActionType.CHAT:
            return False
        if requested_force_tool:
            return False
        request_plan = getattr(llm_request, "request_plan", None)
        if request_plan is None:
            return False
        return getattr(request_plan, "planner_mode", None) == "select_tools"

    @staticmethod
    def _apply_request_plan_tool_routing(
        llm_request: Any,
        *,
        requested_force_tool: Optional[str] = None,
    ) -> None:
        """Apply request-plan tool ownership to the live request."""
        if not llm_request or requested_force_tool:
            return

        request_plan = getattr(llm_request, "request_plan", None)
        if request_plan is None:
            return

        if getattr(request_plan, "planner_mode", None) == "select_tools":
            llm_request.force_tool = None
            return

        if (
            getattr(request_plan, "tool_required", False)
            and getattr(request_plan, "primary_tool", None)
        ):
            llm_request.force_tool = request_plan.primary_tool

    def _activate_request_planner_mode(
        self,
        llm_request: Any,
        action: Any,
        requested_force_tool: Optional[str] = None,
    ) -> None:
        """Enable planner mode and preserve the final chat prompt."""
        if not llm_request:
            return
        request_plan = getattr(llm_request, "request_plan", None)
        if request_plan is not None:
            llm_request.planner_mode = getattr(
                request_plan,
                "planner_mode",
                None,
            )
        if (
            getattr(llm_request, "planner_mode", None) is None
            and self._should_auto_activate_document_planner(
                llm_request,
                action,
                requested_force_tool,
            )
        ):
            llm_request.planner_mode = "select_tools"
        if getattr(llm_request, "planner_mode", None) != "select_tools":
            return
        if request_plan is not None:
            if not getattr(request_plan, "planner_mode", None):
                request_plan.planner_mode = "select_tools"
            if (
                len(getattr(request_plan, "allowed_tool_names", []) or []) <= 1
                and getattr(llm_request, "rag_files", None)
            ):
                request_plan.allowed_tool_names = [
                    "inspect_loaded_documents",
                    "analyze_loaded_document",
                    "rag_search",
                ]
        if getattr(llm_request, "final_system_prompt", None):
            return
        llm_request.final_system_prompt = self.get_system_prompt_with_context(
            LLMActionType.CHAT,
            None,
            None,
        )

    def _request_planner_system_prompt(
        self,
        llm_request: Any,
        action: Any,
    ) -> Optional[str]:
        """Return the planner-stage prompt override for the request."""
        if not llm_request:
            return None
        if getattr(llm_request, "system_prompt", None):
            return None
        if getattr(llm_request, "planner_mode", None) != "select_tools":
            return None
        return self.get_tool_planner_system_prompt(
            action,
            tool_categories=getattr(llm_request, "tool_categories", None),
            planner_tool_hints=getattr(
                llm_request,
                "planner_tool_hints",
                None,
            ),
            attached_document_capabilities=getattr(
                llm_request,
                "attached_document_capabilities",
                None,
            ),
            attached_document_total_tokens=getattr(
                llm_request,
                "attached_document_total_tokens",
                0,
            ),
            attached_document_total_characters=getattr(
                llm_request,
                "attached_document_total_characters",
                0,
            ),
        )

    @staticmethod
    def _build_document_request_route(llm_request: Any) -> Any:
        """Return one request-scoped document route shim from metadata."""
        if llm_request is None:
            return None

        request_plan = getattr(llm_request, "request_plan", None)
        if isinstance(request_plan, RequestPlan):
            intent = getattr(request_plan, "document_query_intent", None)
            summary_focus = getattr(
                request_plan,
                "document_summary_focus",
                None,
            )
            answer_mode = getattr(request_plan, "document_answer_mode", None)
            force_tool = getattr(request_plan, "primary_tool", None)
            if any((intent, summary_focus, answer_mode, force_tool)):
                return SimpleNamespace(
                    intent=intent,
                    summary_focus=summary_focus,
                    answer_mode=answer_mode,
                    force_tool=force_tool,
                )

        intent = getattr(llm_request, "document_query_intent", None)
        summary_focus = getattr(llm_request, "document_summary_focus", None)
        answer_mode = getattr(llm_request, "document_answer_mode", None)
        force_tool = getattr(llm_request, "document_primary_tool", None)
        if not any((intent, summary_focus, answer_mode, force_tool)):
            return None
        return SimpleNamespace(
            intent=intent,
            summary_focus=summary_focus,
            answer_mode=answer_mode,
            force_tool=force_tool,
        )

    def _emit_request_preprocess_status(
        self,
        llm_request: Any,
        prompt: str,
        *,
        status: str,
        details: str,
    ) -> None:
        """Emit one status update for the request-preprocess stage."""
        request_id = getattr(self, "_current_request_id", None)
        tool_status_id = (
            f"request_preprocess_{request_id}"
            if request_id
            else "request_preprocess"
        )
        self.emit_signal(
            SignalCode.LLM_TOOL_STATUS_SIGNAL,
            {
                "tool_id": tool_status_id,
                "tool_name": "request_preprocessor",
                "query": str(prompt or "")[:100],
                "status": status,
                "details": details,
                "conversation_id": getattr(self, "_conversation_id", None),
                "request_id": request_id,
                "metadata": self._request_debug_metadata(llm_request),
                "timestamp": datetime.utcnow().isoformat(),
            },
        )

    def _apply_request_preprocess(
        self,
        llm_request: Any,
        prompt: str,
        action: Any,
        conversation: Any,
        *,
        explicit_force_tool: Optional[str] = None,
    ) -> None:
        """Run the LLM request preprocessor and persist its result."""
        if llm_request is None:
            return
        if explicit_force_tool:
            llm_request.preprocessed_primary_tool = explicit_force_tool
            llm_request.request_plan = RequestPlan(
                rewrite_needed=False,
                rewritten_query=str(prompt or "").strip(),
                tool_required=True,
                tool_categories=list(
                    getattr(llm_request, "tool_categories", []) or []
                ),
                allowed_tool_names=[explicit_force_tool],
                primary_tool=explicit_force_tool,
                planner_tool_hints=[explicit_force_tool],
            )
            return

        preprocess_request = getattr(self, "_preprocess_request", None)
        if not callable(preprocess_request):
            return

        self._emit_request_preprocess_status(
            llm_request,
            prompt,
            status="starting",
            details="Analyzing conversation context and rewriting the request if needed...",
        )

        result = preprocess_request(
            prompt,
            action=action,
            llm_request=llm_request,
            conversation=conversation,
        )
        if result is None:
            self._emit_request_preprocess_status(
                llm_request,
                prompt,
                status="failed",
                details="Request preprocessing was unavailable; continuing without a rewritten request.",
            )
            return

        request_plan = self._coerce_request_plan(result)
        llm_request.request_plan = request_plan

        rewritten_prompt = ""
        if request_plan is not None:
            rewritten_prompt = str(
                getattr(request_plan, "rewritten_query", "") or ""
            ).strip()
        if not rewritten_prompt:
            rewritten_prompt = str(
                result.get("rewritten_query", "") or ""
            ).strip()

        rewrite_needed = bool(result.get("rewrite_needed"))
        if request_plan is not None:
            rewrite_needed = bool(getattr(request_plan, "rewrite_needed", False))

        if rewrite_needed and rewritten_prompt:
            llm_request.rewritten_prompt = rewritten_prompt
        else:
            llm_request.rewritten_prompt = None

        plan_tool_categories = list(result.get("tool_categories") or [])
        if request_plan is not None:
            plan_tool_categories = list(
                getattr(request_plan, "tool_categories", []) or []
            )
        llm_request.tool_categories = plan_tool_categories

        primary_tool = result.get("primary_tool")
        if request_plan is not None:
            primary_tool = getattr(request_plan, "primary_tool", None)
        llm_request.preprocessed_primary_tool = primary_tool
        llm_request.document_query_intent = getattr(
            request_plan,
            "document_query_intent",
            result.get("document_query_intent"),
        )
        llm_request.document_summary_focus = getattr(
            request_plan,
            "document_summary_focus",
            result.get("document_summary_focus"),
        )
        llm_request.document_answer_mode = getattr(
            request_plan,
            "document_answer_mode",
            result.get("document_answer_mode"),
        )
        llm_request.planner_tool_hints = list(
            getattr(
                request_plan,
                "planner_tool_hints",
                result.get("planner_tool_hints") or [],
            )
            or []
        )

        if primary_tool in self.DOCUMENT_TOOL_NAMES:
            llm_request.document_primary_tool = primary_tool
        else:
            llm_request.document_primary_tool = None

        self._current_document_query_route = self._build_document_request_route(
            llm_request
        )

        details_parts = []
        if llm_request.rewritten_prompt:
            details_parts.append(
                f"rewritten query: {llm_request.rewritten_prompt[:80]}"
            )
        categories = list(llm_request.tool_categories or [])
        details_parts.append(
            "categories: "
            + (
                ", ".join(categories)
                if categories
                else "none"
            )
        )
        if primary_tool:
            details_parts.append(f"primary tool: {primary_tool}")

        self._emit_request_preprocess_status(
            llm_request,
            prompt,
            status="completed",
            details=" | ".join(details_parts),
        )

    def _request_preprocess_system_prompt(
        self,
        llm_request: Any,
        action: Any,
        system_prompt: Optional[str],
    ) -> Optional[str]:
        """Append rewritten-query guidance to the active system prompt."""
        if llm_request is None:
            return system_prompt

        rewritten_prompt = getattr(llm_request, "rewritten_prompt", None)
        primary_tool = getattr(llm_request, "preprocessed_primary_tool", None)
        request_plan = getattr(llm_request, "request_plan", None)
        planner_mode = getattr(llm_request, "planner_mode", None)
        if request_plan is not None and getattr(
            request_plan,
            "planner_mode",
            None,
        ):
            planner_mode = request_plan.planner_mode
        if not rewritten_prompt and (
            not primary_tool or planner_mode == "select_tools"
        ):
            return system_prompt

        base_prompt = system_prompt
        if base_prompt is None:
            base_prompt = self.get_system_prompt_with_context(
                action,
                None,
                None,
            )

        additions = [
            "",
            "Internal request preprocess:",
            "Use the canonical request below when choosing tools and tool arguments.",
            "The original user message remains part of the visible conversation history.",
        ]
        if rewritten_prompt:
            additions.extend(
                [
                    "Canonical request:",
                    rewritten_prompt,
                ]
            )
        if primary_tool and planner_mode != "select_tools":
            additions.append(f"Most likely first tool: {primary_tool}")
        return "\n".join([base_prompt, *additions])

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
        self._current_document_query_route = None
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
            self._prepare_request_tooling(
                data,
                llm_request,
                conversation=conversation,
            )
        )
        rag_error = self._prepare_request_rag(
            data,
            llm_request,
            selected_categories,
        )
        if rag_error is not None:
            return rag_error
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

    def _prepare_request_tooling(
        self,
        data: Dict[str, Any],
        llm_request: Any,
        *,
        conversation: Any = None,
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
        requested_force_tool = (
            getattr(llm_request, "force_tool", None) if llm_request else None
        )
        self._apply_request_preprocess(
            llm_request,
            prompt,
            action,
            conversation,
            explicit_force_tool=requested_force_tool,
        )
        self._activate_request_planner_mode(
            llm_request,
            action,
            requested_force_tool,
        )
        self._apply_request_plan_tool_routing(
            llm_request,
            requested_force_tool=requested_force_tool,
        )
        allowed_tool_names = self._document_planner_allowed_tool_names(
            llm_request,
        )
        planner_system_prompt = self._request_planner_system_prompt(
            llm_request,
            action,
        )
        if planner_system_prompt is not None:
            system_prompt = planner_system_prompt
        system_prompt = self._request_preprocess_system_prompt(
            llm_request,
            action,
            system_prompt,
        )

        if llm_request and llm_request.tool_categories is not None:
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
                allowed_tool_names=allowed_tool_names,
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

    def _prepare_request_rag(
        self,
        data: Dict[str, Any],
        llm_request: Any,
        selected_categories: List[str],
    ) -> Optional[Dict[str, Any]]:
        """Ensure request-provided or inferred RAG files are indexed."""
        if llm_request and getattr(llm_request, "rag_files", None):
            rag_error = self._ensure_request_rag_files(llm_request.rag_files)
            if rag_error is not None:
                return rag_error

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
                        rag_error = self._ensure_request_rag_files(
                            candidates
                        )
                        if rag_error is not None:
                            return rag_error
        except Exception:
            self.logger.debug(
                "Auto attachment of RAG files failed, continuing without "
                "local RAG."
            )
        return None

    def _ensure_request_rag_files(
        self,
        rag_files: Any,
    ) -> Optional[Dict[str, Any]]:
        """Load and index request-provided RAG files."""
        try:
            if hasattr(self, "ensure_indexed_files"):
                success = self.ensure_indexed_files(rag_files)
                if success:
                    return None
                if getattr(self, "_rag_retry_after_download", False):
                    error_message = (
                        getattr(self, "_last_rag_index_error", None)
                        or "Embedding model download in progress."
                    )
                    return {
                        "response": (
                            "Error: the embedding model required for "
                            "document search is still downloading. "
                            "AIRunner will retry your request "
                            "automatically when the download finishes."
                        ),
                        "error": error_message,
                        "retry_after_download": True,
                    }
                return None

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
        return None

    def _load_rag_document_payload(self, doc: Dict[str, Any]) -> None:
        """Load one request-provided document payload into RAG."""
        file_type = str(doc.get("file_type", "")).lower()
        content = doc.get("content")
        source_name = doc.get("source_name", "web_content")
        if file_type in [".epub", ".mobi", ".pdf"]:
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
        _ = llm_request
        targets = [self._chat_model]
        if self._workflow_manager:
            targets.append(
                getattr(self._workflow_manager, "_original_chat_model", None)
            )

        for target in targets:
            if target is None or not hasattr(target, "enable_thinking"):
                continue
            try:
                setattr(target, "enable_thinking", True)
            except Exception:
                continue
        return []

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