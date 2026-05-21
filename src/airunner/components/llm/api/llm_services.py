from airunner.components.application.api.api_service_base import APIServiceBase
from airunner.components.llm.managers.llm_request import LLMRequest
from airunner.components.llm.managers.llm_response import LLMResponse
from airunner.components.llm.utils.thinking_parser import (
    detect_thinking_close_tag,
    detect_thinking_open_tag,
    strip_thinking_tags,
)
from airunner.components.llm.utils.stream_text import (
    append_stream_text,
    prepare_stream_chunk,
)
from airunner.daemon_client.daemon_connection_state import (
    DaemonConnectionState,
)
from airunner.enums import SignalCode
from airunner.enums import LLMActionType
from dataclasses import dataclass, field
import threading
import uuid
from typing import Optional, List


@dataclass
class _DaemonStreamState:
    """Track one daemon-backed GUI stream."""

    in_thinking_block: bool = False
    thinking_tag_format: str = ""
    thinking_content: list[str] = field(default_factory=list)
    visible_sequence_number: int = 0
    visible_text: str = ""
    hold_visible_output: bool = False
    pending_visible_parts: list[str] = field(default_factory=list)


class LLMAPIService(APIServiceBase):
    """LLM API service providing signal-based LLM operations."""

    def __init__(self):
        super().__init__()

    def chatbot_changed(self):
        self.emit_signal(SignalCode.CHATBOT_CHANGED)

    def send_request(
        self,
        prompt,
        command: Optional[str] = None,
        llm_request: Optional[LLMRequest] = None,
        action: LLMActionType = LLMActionType.CHAT,
        do_tts_reply: bool = True,
        node_id: Optional[str] = None,
        request_id: Optional[str] = None,
        callback: Optional[callable] = None,
        conversation_id: Optional[int] = None,
        enable_consciousness: Optional[bool] = None,
        **kwargs,
    ):
        """Send an LLM generation request.

        Args:
            prompt: The user's input text
            command: Optional command string
            llm_request: Optional LLM parameters
            action: The action type (CHAT, CODE, etc.)
            do_tts_reply: Whether to convert reply to speech
            node_id: Optional node identifier
            request_id: Optional unique request identifier for correlation
            callback: Optional callback function for responses
            conversation_id: Optional conversation ID to associate with the request
        """
        # Use action-optimized defaults if no explicit request provided
        # Accept backwards-compatible extra kwargs such as 'system_prompt'
        system_prompt = kwargs.pop("system_prompt", None)
        search_hints = kwargs.pop("search_hints", None)
        llm_request = llm_request or LLMRequest.for_action(action)
        if system_prompt:
            try:
                setattr(llm_request, "system_prompt", system_prompt)
            except Exception:
                self.logger.exception(
                    "Failed to set system_prompt on llm_request"
                )
        if kwargs:
            # Warn about any other unknown kwargs but do not raise
            self.logger.warning(
                f"LLMAPIService.send_request received unknown kwargs: {list(kwargs.keys())} - ignoring"
            )
        llm_request.do_tts_reply = do_tts_reply

        resolved_request_id = request_id or str(uuid.uuid4())

        data = {
            "llm_request": True,
            "request_id": resolved_request_id,
            "request_data": {
                "action": action,
                "prompt": prompt,
                "command": command,
                "llm_request": llm_request,
                "do_tts_reply": do_tts_reply,
                "request_id": resolved_request_id,
            },
        }

        if search_hints is not None:
            data["request_data"]["search_hints"] = search_hints
        if conversation_id is not None:
            data["conversation_id"] = conversation_id
        if node_id is not None:
            data["node_id"] = node_id
        if enable_consciousness is not None:
            data["enable_consciousness"] = enable_consciousness

        if callback:
            from airunner.utils.application.signal_mediator import (
                SignalMediator,
            )

            mediator = SignalMediator()
            mediator.register_pending_request(resolved_request_id, callback)

        if self._send_request_via_daemon(
            prompt,
            llm_request,
            action,
            resolved_request_id,
            search_hints,
            conversation_id,
            node_id,
            enable_consciousness,
            signal_data=data,
        ):
            self.logger.info("LLM API: Daemon request queued")
            return

        LLMAPIService._emit_local_generation_request(self, data)

    def clear_history(self, **kwargs):
        self.emit_signal(SignalCode.LLM_CLEAR_HISTORY_SIGNAL, kwargs)

    def converation_deleted(self, conversation_id: int):
        self.emit_signal(
            SignalCode.CONVERSATION_DELETED,
            {"conversation_id": conversation_id},
        )

    def model_changed(self, model_service: str):
        self.update_llm_generator_settings(model_service=model_service)
        self.emit_signal(
            SignalCode.LLM_MODEL_CHANGED,
            {
                "model_service": model_service,
                "reload_runtime": False,
            },
        )

    def reload_rag(self, target_files: Optional[List[str]] = None):
        self.emit_signal(
            SignalCode.RAG_RELOAD_INDEX_SIGNAL,
            {"target_files": target_files} if target_files else None,
        )

    def unload_rag(self) -> None:
        """Unload the RAG embedding runtime without unloading the LLM."""
        self.emit_signal(SignalCode.RAG_UNLOAD_SIGNAL, {})

    def load_conversation(self, conversation_id: int):
        self.emit_signal(
            SignalCode.QUEUE_LOAD_CONVERSATION,
            {"action": "load_conversation", "index": conversation_id},
        )

    def interrupt(self):
        client = self._daemon_client()
        if client is not None:
            try:
                client.interrupt_llm()
                return
            except RuntimeError:
                pass

        print("[LLM INTERRUPT] Emitting INTERRUPT_PROCESS_SIGNAL")
        self.emit_signal(SignalCode.INTERRUPT_PROCESS_SIGNAL)

    def unload(self, data: Optional[dict] = None) -> None:
        """Unload the active LLM without blocking the caller."""
        payload = dict(data or {})
        if LLMAPIService._local_llm_should_handle_unload(self):
            self._emit_local_unload_request(payload)
            return

        client = self._daemon_client()
        if client is None:
            self._emit_local_unload_request(payload)
            return

        thread = threading.Thread(
            target=LLMAPIService._run_daemon_unload,
            args=(self, client, payload),
            daemon=True,
        )
        thread.start()

    def _emit_local_unload_request(self, payload: dict) -> None:
        """Emit one best-effort local unload request."""
        self.emit_signal(SignalCode.INTERRUPT_PROCESS_SIGNAL)
        self.emit_signal(SignalCode.LLM_UNLOAD_SIGNAL, payload)

    def _local_llm_should_handle_unload(self) -> bool:
        """Return True when the GUI-local worker owns the live LLM."""
        from airunner.enums import ModelStatus

        worker_manager_getter = getattr(self, "_worker_manager", None)
        if not callable(worker_manager_getter):
            return False

        worker_manager = worker_manager_getter()
        if worker_manager is None:
            return False

        worker = getattr(worker_manager, "_llm_generate_worker", None)
        if worker is None:
            return False

        status_getter = getattr(worker, "current_model_status", None)
        if callable(status_getter):
            try:
                status = status_getter()
            except Exception:
                status = None
            if status in (ModelStatus.LOADING, ModelStatus.LOADED):
                return True

        return getattr(worker, "_pending_llm_request", None) is not None

    def _run_daemon_unload(self, client, payload: dict) -> None:
        """Interrupt and queue one daemon-side LLM unload."""
        try:
            client.interrupt_llm()
        except RuntimeError:
            pass

        try:
            client.unload_local_llm(auto_start=False)
        except RuntimeError:
            self._emit_local_unload_request(payload)

    def delete_messages_after_id(self, message_id: int):
        self.emit_signal(
            SignalCode.DELETE_MESSAGES_AFTER_ID, {"message_id": message_id}
        )

    def finalize_image_generated_by_llm(self, _data):
        """
        Callback function to be called after the image has been generated.
        """
        # Ask the LLM to provide a brief confirmation in the current conversation style
        self.send_request(
            "The image request has completed. Write a single concise reply (1 short sentence) acknowledging the generated image.",
            action=LLMActionType.CHAT,
            do_tts_reply=True,
        )

    def send_llm_text_streamed_signal(self, response: LLMResponse):
        # Include request_id at top level for SignalMediator correlation
        data = {"response": response}
        if response.request_id:
            data["request_id"] = response.request_id
        else:
            try:
                self.logger.warning(
                    "[STREAM] Emitting streamed response without request_id; pending HTTP callbacks will not be notified"
                )
            except Exception:
                pass
        if self._forward_tts_stream_signal(data):
            data["_skip_worker_manager_tts"] = True
        self.emit_signal(SignalCode.LLM_TEXT_STREAMED_SIGNAL, data)

    def send_llm_thinking_signal(
        self,
        status: str,
        content: str,
        request_id: Optional[str] = None,
    ) -> None:
        """Emit one thinking-status update for the chat UI."""
        self.emit_signal(
            SignalCode.LLM_THINKING_SIGNAL,
            self._thinking_signal_payload(status, content, request_id),
        )

    def _thinking_signal_payload(
        self,
        status: str,
        content: str,
        request_id: Optional[str] = None,
    ) -> dict:
        """Build one thinking-signal payload and fast-path TTS state."""
        data = {
            "status": status,
            "content": content,
            "request_id": request_id,
        }
        if self._forward_tts_thinking_signal(data):
            data["_skip_worker_manager_tts"] = True
        return data

    def _forward_tts_stream_signal(self, data: dict) -> bool:
        """Forward one streamed LLM chunk directly to the GUI TTS worker."""
        worker = self._tts_stream_worker()
        handler = getattr(worker, "on_llm_text_streamed_signal", None)
        if not callable(handler):
            return False
        handler(dict(data))
        return True

    def _forward_tts_thinking_signal(self, data: dict) -> bool:
        """Forward one thinking update directly to the GUI TTS worker."""
        worker = self._tts_stream_worker()
        handler = getattr(worker, "on_llm_thinking_signal", None)
        if not callable(handler):
            return False
        handler(dict(data))
        return True

    def _tts_stream_worker(self):
        """Return the live GUI TTS worker when one exists."""
        worker_manager = self._worker_manager()
        if worker_manager is None:
            return None
        resolver = getattr(worker_manager, "_stream_tts_worker", None)
        if callable(resolver):
            return resolver()
        return getattr(worker_manager, "tts_generator_worker", None)

    def _worker_manager(self):
        """Return the GUI worker manager when one is available."""
        resolved_api = LLMAPIService._resolve_api_instance()
        for candidate in (
            getattr(getattr(self, "api", None), "main_window", None),
            getattr(
                getattr(getattr(self, "api", None), "app", None),
                "main_window",
                None,
            ),
            getattr(resolved_api, "main_window", None),
        ):
            if candidate is None:
                continue
            worker_manager = getattr(candidate, "worker_manager", None)
            if worker_manager is not None:
                return worker_manager
        return None

    def _prewarm_tts_runtime_for_request(
        self,
        llm_request: LLMRequest,
    ) -> None:
        """Start sidecar TTS early when one daemon reply will be spoken."""
        worker_manager = self._worker_manager()
        if worker_manager is None:
            return
        app_settings = getattr(worker_manager, "application_settings", None)
        if not getattr(llm_request, "do_tts_reply", False) and not bool(
            getattr(app_settings, "tts_enabled", False)
        ):
            return
        prewarm = getattr(worker_manager, "_start_tts_runtime_prewarm", None)
        if callable(prewarm):
            prewarm()

    def _send_request_via_daemon(
        self,
        prompt: str,
        llm_request: LLMRequest,
        action: LLMActionType,
        request_id: Optional[str],
        search_hints: Optional[dict],
        conversation_id: Optional[int],
        node_id: Optional[str],
        enable_consciousness: Optional[bool],
        signal_data: Optional[dict] = None,
    ) -> bool:
        """Route a GUI request through the daemon when that client is ready."""
        client = self._daemon_client()
        if client is None or not request_id:
            return False
        if getattr(llm_request, "images", None):
            return False

        thread = threading.Thread(
            target=LLMAPIService._run_daemon_request_or_fallback,
            args=(
                self,
                client,
                prompt,
                llm_request,
                action,
                request_id,
                search_hints,
                conversation_id,
                node_id,
                enable_consciousness,
                signal_data,
            ),
            daemon=True,
        )
        thread.start()
        return True

    def _emit_local_generation_request(self, data: dict) -> None:
        """Emit one local-worker request when daemon routing is skipped."""
        self.emit_signal(SignalCode.LLM_TEXT_GENERATE_REQUEST_SIGNAL, data)
        self.logger.info("LLM API: Signal emitted")

    def _daemon_is_immediately_available(self, client) -> bool:
        """Return True when one daemon can accept a request right now."""
        if getattr(client, "state", None) is DaemonConnectionState.CONNECTED:
            return True
        availability_check = getattr(client, "is_available", None)
        if callable(availability_check):
            try:
                return bool(availability_check(timeout_seconds=0.2))
            except TypeError:
                return bool(availability_check())
        return bool(client.ensure_connected(auto_start=False))

    def _run_daemon_request_or_fallback(
        self,
        client,
        prompt: str,
        llm_request: LLMRequest,
        action: LLMActionType,
        request_id: str,
        search_hints: Optional[dict],
        conversation_id: Optional[int],
        node_id: Optional[str],
        enable_consciousness: Optional[bool],
        signal_data: Optional[dict],
    ) -> None:
        """Use the daemon when it is already reachable, else fall back."""
        if not LLMAPIService._daemon_is_immediately_available(self, client):
            if signal_data is not None:
                LLMAPIService._emit_local_generation_request(
                    self,
                    signal_data,
                )
            return

        LLMAPIService._prewarm_tts_runtime_for_request(self, llm_request)
        self._stream_daemon_request(
            client,
            prompt,
            llm_request,
            action,
            request_id,
            search_hints,
            conversation_id,
            node_id,
            enable_consciousness,
        )

    def _stream_daemon_request(
        self,
        client,
        prompt: str,
        llm_request: LLMRequest,
        action: LLMActionType,
        request_id: str,
        search_hints: Optional[dict],
        conversation_id: Optional[int],
        node_id: Optional[str],
        enable_consciousness: Optional[bool],
    ) -> None:
        """Emit streamed LLM responses received from the daemon client."""
        state = _DaemonStreamState(
            hold_visible_output=bool(
                getattr(llm_request, "force_tool", None)
            )
        )
        try:
            for chunk in client.stream_llm_request(
                prompt,
                llm_request,
                action,
                request_id,
                search_hints=search_hints,
                conversation_id=conversation_id,
                node_id=node_id,
                enable_consciousness=enable_consciousness,
            ):
                if chunk.get("keepalive"):
                    continue
                self._forward_daemon_chunk(
                    chunk,
                    state=state,
                    request_id=request_id,
                    action=action,
                    node_id=node_id,
                )
        except RuntimeError as exc:
            self.send_llm_text_streamed_signal(
                LLMResponse(
                    message=f"Error invoking LLM: {exc}",
                    is_first_message=True,
                    is_end_of_message=True,
                    action=action,
                    node_id=node_id,
                    request_id=request_id,
                    is_system_message=True,
                )
            )

    def _forward_daemon_chunk(
        self,
        chunk: dict,
        *,
        state: _DaemonStreamState,
        request_id: str,
        action: LLMActionType,
        node_id: Optional[str],
    ) -> None:
        """Translate one daemon NDJSON chunk into GUI-visible signals."""
        if bool(chunk.get("error", False)):
            self.send_llm_text_streamed_signal(
                self._build_visible_daemon_response(
                    chunk,
                    state=state,
                    message=chunk.get("message", "") or "",
                    is_end_of_message=bool(
                        chunk.get("is_end_of_message", False)
                    ),
                    request_id=request_id,
                    action=action,
                    node_id=node_id,
                )
            )
            return

        if self._forward_structured_daemon_chunk(
            chunk,
            state=state,
            request_id=request_id,
            action=action,
            node_id=node_id,
        ):
            return

        if (
            state.hold_visible_output
            and bool(chunk.get("is_first_message", False))
            and state.pending_visible_parts
        ):
            self._finish_pending_daemon_visible_output(
                chunk,
                state=state,
                request_id=request_id,
                action=action,
                node_id=node_id,
            )

        visible_parts = self._extract_visible_daemon_text(
            chunk.get("message", "") or "",
            state,
            request_id=request_id,
        )
        if bool(chunk.get("is_end_of_message", False)):
            self._finish_daemon_thinking(state, request_id=request_id)

        if visible_parts:
            if state.hold_visible_output:
                state.pending_visible_parts.extend(visible_parts)
                if bool(chunk.get("is_end_of_message", False)):
                    self._finish_pending_daemon_visible_output(
                        chunk,
                        state=state,
                        request_id=request_id,
                        action=action,
                        node_id=node_id,
                    )
            else:
                self._emit_visible_daemon_parts(
                    visible_parts,
                    chunk=chunk,
                    state=state,
                    request_id=request_id,
                    action=action,
                    node_id=node_id,
                )
            return

        if state.hold_visible_output and bool(
            chunk.get("is_end_of_message", False)
        ):
            self._finish_pending_daemon_visible_output(
                chunk,
                state=state,
                request_id=request_id,
                action=action,
                node_id=node_id,
            )
            return

        if state.visible_sequence_number > 0 and bool(
            chunk.get("is_end_of_message", False)
        ):
            self.send_llm_text_streamed_signal(
                self._build_visible_daemon_response(
                    chunk,
                    state=state,
                    message="",
                    is_end_of_message=True,
                    request_id=request_id,
                    action=action,
                    node_id=node_id,
                )
            )

    def _forward_structured_daemon_chunk(
        self,
        chunk: dict,
        *,
        state: _DaemonStreamState,
        request_id: str,
        action: LLMActionType,
        node_id: Optional[str],
    ) -> bool:
        """Prefer typed daemon chunk metadata when it is available."""
        message_type = self._daemon_message_type(chunk)
        if message_type is None:
            return False
        if message_type == "thinking":
            self._forward_structured_thinking_chunk(
                chunk,
                state=state,
                request_id=request_id,
            )
            return True
        if message_type == "assistant":
            self._forward_structured_assistant_chunk(
                chunk,
                state=state,
                request_id=request_id,
                action=action,
                node_id=node_id,
            )
            return True
        if message_type in {"tool_call", "tool_result", "tool_status"}:
            self._reset_structured_hidden_output(state)
            if bool(chunk.get("is_end_of_message", False)):
                self._finish_daemon_thinking(state, request_id=request_id)
            return True
        return False

    @staticmethod
    def _daemon_message_type(chunk: dict) -> str | None:
        """Return one normalized daemon message type."""
        message_type = chunk.get("message_type")
        if not isinstance(message_type, str):
            return None
        normalized = message_type.strip().lower()
        return normalized or None

    @staticmethod
    def _reset_structured_hidden_output(state: _DaemonStreamState) -> None:
        """Clear any buffered compatibility state for typed chunks."""
        state.hold_visible_output = False
        state.pending_visible_parts = []

    def _forward_structured_thinking_chunk(
        self,
        chunk: dict,
        *,
        state: _DaemonStreamState,
        request_id: str,
    ) -> None:
        """Forward one typed thinking chunk to the existing thinking UI."""
        content = chunk.get("thinking_content")
        if not isinstance(content, str):
            content = chunk.get("message", "") or ""
        if bool(chunk.get("is_first_message", False)) or not state.in_thinking_block:
            self._start_daemon_thinking(
                state,
                "structured",
                request_id=request_id,
            )
        self._append_daemon_thinking(state, content, request_id=request_id)
        if bool(chunk.get("is_end_of_message", False)):
            self._finish_daemon_thinking(state, request_id=request_id)

    def _forward_structured_assistant_chunk(
        self,
        chunk: dict,
        *,
        state: _DaemonStreamState,
        request_id: str,
        action: LLMActionType,
        node_id: Optional[str],
    ) -> None:
        """Forward one typed assistant chunk without legacy heuristics."""
        if state.in_thinking_block:
            self._finish_daemon_thinking(state, request_id=request_id)
        self._reset_structured_hidden_output(state)
        message = chunk.get("message", "") or ""
        if message:
            self._emit_visible_daemon_parts(
                [message],
                chunk=chunk,
                state=state,
                request_id=request_id,
                action=action,
                node_id=node_id,
            )
            return
        if state.visible_sequence_number > 0 and bool(
            chunk.get("is_end_of_message", False)
        ):
            self.send_llm_text_streamed_signal(
                self._build_visible_daemon_response(
                    chunk,
                    state=state,
                    message="",
                    is_end_of_message=True,
                    request_id=request_id,
                    action=action,
                    node_id=node_id,
                )
            )

    def _finish_pending_daemon_visible_output(
        self,
        chunk: dict,
        *,
        state: _DaemonStreamState,
        request_id: str,
        action: LLMActionType,
        node_id: Optional[str],
    ) -> None:
        """Release or discard one buffered daemon substream."""
        pending_parts = list(state.pending_visible_parts)
        state.pending_visible_parts = []
        state.hold_visible_output = False
        if not pending_parts:
            return

        pending_text = "".join(pending_parts)
        if self._daemon_output_looks_like_tool_turn(pending_text, chunk):
            return

        self._emit_visible_daemon_parts(
            pending_parts,
            chunk=chunk,
            state=state,
            request_id=request_id,
            action=action,
            node_id=node_id,
        )

    def _daemon_output_looks_like_tool_turn(
        self,
        text: str,
        chunk: dict,
    ) -> bool:
        """Return whether buffered daemon text looks like tool planning."""
        if bool(chunk.get("tools") or chunk.get("tool_calls")):
            return True

        stripped = str(text or "").strip()
        if not stripped:
            return False
        if self._daemon_text_looks_like_tool_call_json(stripped):
            return True

        normalized = " ".join(stripped.lower().split())
        markers = (
            "let me call the",
            "i'll call the",
            "i will call the",
            "i'm calling the",
            "i am calling the",
            "calling the search tool",
            "rag_search tool",
        )
        return any(marker in normalized for marker in markers)

    @staticmethod
    def _daemon_text_looks_like_tool_call_json(text: str) -> bool:
        """Return whether daemon-visible text matches tool-call JSON."""
        stripped = str(text or "").strip()
        if not stripped.startswith("{"):
            return False
        if ('"name"' in stripped or '"tool"' in stripped) and (
            '"arguments"' in stripped or '"args"' in stripped
        ):
            return True
        if '"tool"' in stripped and any(
            key in stripped
            for key in (
                '"query"',
                '"prompt"',
                '"url"',
                '"path"',
                '"text"',
                '"content"',
            )
        ):
            return True
        return False

    def _emit_visible_daemon_parts(
        self,
        visible_parts: List[str],
        *,
        chunk: dict,
        state: _DaemonStreamState,
        request_id: str,
        action: LLMActionType,
        node_id: Optional[str],
    ) -> None:
        """Emit one or more visible response chunks for the GUI."""
        last_index = len(visible_parts) - 1
        chunk_done = bool(chunk.get("is_end_of_message", False))
        for index, part in enumerate(visible_parts):
            # visible_parts already come from _extract_visible_daemon_text(),
            # so trimming here would incorrectly drop leading spaces between
            # streamed word chunks.
            cleaned_part = part
            if not cleaned_part:
                continue
            normalized_part = prepare_stream_chunk(
                state.visible_text,
                cleaned_part,
            )
            if not normalized_part:
                continue
            state.visible_text = append_stream_text(
                state.visible_text,
                cleaned_part,
            )
            self.send_llm_text_streamed_signal(
                self._build_visible_daemon_response(
                    chunk,
                    state=state,
                    message=normalized_part,
                    is_end_of_message=chunk_done and index == last_index,
                    request_id=request_id,
                    action=action,
                    node_id=node_id,
                )
            )

    def _extract_visible_daemon_text(
        self,
        message: str,
        state: _DaemonStreamState,
        *,
        request_id: str,
    ) -> List[str]:
        """Split one daemon chunk into visible text and thinking updates."""
        visible_parts: List[str] = []
        remaining = message
        while remaining:
            if state.in_thinking_block:
                found_close, before_close, after_close = (
                    detect_thinking_close_tag(
                        remaining,
                        state.thinking_tag_format,
                    )
                )
                if found_close:
                    self._append_daemon_thinking(
                        state,
                        before_close,
                        request_id=request_id,
                    )
                    self._finish_daemon_thinking(
                        state,
                        request_id=request_id,
                    )
                    remaining = after_close
                    continue
                self._append_daemon_thinking(
                    state,
                    remaining,
                    request_id=request_id,
                )
                break

            found_open, tag_format, before_open, after_open = (
                detect_thinking_open_tag(remaining)
            )
            if not found_open:
                visible_parts.append(remaining)
                break
            if before_open:
                visible_parts.append(before_open)
            self._start_daemon_thinking(
                state,
                tag_format,
                request_id=request_id,
            )
            remaining = after_open
        return visible_parts

    def _start_daemon_thinking(
        self,
        state: _DaemonStreamState,
        tag_format: str,
        *,
        request_id: str,
    ) -> None:
        """Mark one daemon stream as being inside a thinking block."""
        state.in_thinking_block = True
        state.thinking_tag_format = tag_format
        state.thinking_content = []
        self.send_llm_thinking_signal("started", "", request_id)

    def _append_daemon_thinking(
        self,
        state: _DaemonStreamState,
        content: str,
        *,
        request_id: str,
    ) -> None:
        """Accumulate one thinking fragment and mirror it to the UI."""
        if not content:
            return
        state.thinking_content.append(content)
        self.send_llm_thinking_signal("streaming", content, request_id)

    def _finish_daemon_thinking(
        self,
        state: _DaemonStreamState,
        *,
        request_id: str,
    ) -> None:
        """Complete one thinking block if the daemon stream is inside one."""
        if not state.in_thinking_block:
            return
        self.send_llm_thinking_signal(
            "completed",
            "".join(state.thinking_content),
            request_id,
        )
        state.in_thinking_block = False
        state.thinking_tag_format = ""
        state.thinking_content = []

    def _build_visible_daemon_response(
        self,
        chunk: dict,
        *,
        state: _DaemonStreamState,
        message: str,
        is_end_of_message: bool,
        request_id: str,
        action: LLMActionType,
        node_id: Optional[str],
    ) -> LLMResponse:
        """Build one GUI-visible response from a daemon NDJSON chunk."""
        state.visible_sequence_number += 1
        response = self._response_from_daemon_chunk(
            chunk,
            request_id=request_id,
            action=action,
            node_id=node_id,
        )
        response.message = message
        response.is_first_message = state.visible_sequence_number == 1
        response.is_end_of_message = is_end_of_message
        response.sequence_number = state.visible_sequence_number
        return response

    def _daemon_client(self):
        """Return the GUI daemon client when one is available."""
        refresher = getattr(self, "refresh_api_reference", None)
        if callable(refresher):
            refreshed_api = refresher()
            if refreshed_api is not None:
                self.api = refreshed_api
        api = getattr(self, "api", None)
        if api is None:
            api = LLMAPIService._resolve_api_instance()
            if api is not None:
                self.api = api
        if api is None or getattr(api, "headless", False):
            return None
        return getattr(api, "daemon_client", None)

    @staticmethod
    def _resolve_api_instance():
        """Resolve the live App/API object when service init ran too early."""
        try:
            from PySide6.QtWidgets import QApplication

            app = QApplication.instance()
            if app is not None:
                return getattr(app, "api", None)
        except Exception:
            pass

        try:
            from airunner.components.server.api.server import get_api

            return get_api()
        except Exception:
            return None

    @staticmethod
    def _response_from_daemon_chunk(
        chunk: dict,
        *,
        request_id: str,
        action: LLMActionType,
        node_id: Optional[str],
    ) -> LLMResponse:
        """Convert one daemon NDJSON chunk into the local response model."""
        response = LLMResponse(
            message=chunk.get("message", "") or "",
            is_first_message=bool(chunk.get("is_first_message", False)),
            is_end_of_message=bool(chunk.get("is_end_of_message", False)),
            action=action,
            node_id=node_id,
            sequence_number=int(chunk.get("sequence_number", 0) or 0),
            request_id=request_id,
            tools=chunk.get("tools") or chunk.get("tool_calls"),
            is_system_message=bool(chunk.get("error", False)),
            message_type=chunk.get("message_type"),
            thinking_content=chunk.get("thinking_content"),
            tool_name=chunk.get("tool_name"),
            tool_arguments=chunk.get("tool_arguments"),
            tool_status=chunk.get("tool_status"),
        )
        usage = chunk.get("usage") or {}
        response.prompt_tokens = usage.get("prompt_tokens")
        response.completion_tokens = usage.get("completion_tokens")
        response.total_tokens = usage.get("total_tokens")
        return response
