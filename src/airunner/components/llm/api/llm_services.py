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
        ):
            self.logger.info("LLM API: Daemon request started")
            return

        self.emit_signal(SignalCode.LLM_TEXT_GENERATE_REQUEST_SIGNAL, data)
        self.logger.info("LLM API: Signal emitted")

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
            SignalCode.LLM_MODEL_CHANGED, {"model_service": model_service}
        )

    def reload_rag(self, target_files: Optional[List[str]] = None):
        self.emit_signal(
            SignalCode.RAG_RELOAD_INDEX_SIGNAL,
            {"target_files": target_files} if target_files else None,
        )

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
        self.emit_signal(SignalCode.LLM_TEXT_STREAMED_SIGNAL, data)

    def send_llm_thinking_signal(self, status: str, content: str) -> None:
        """Emit one thinking-status update for the chat UI."""
        self.emit_signal(
            SignalCode.LLM_THINKING_SIGNAL,
            {"status": status, "content": content},
        )

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
    ) -> bool:
        """Route a GUI request through the daemon when that client is ready."""
        client = self._daemon_client()
        if client is None or not request_id:
            return False
        if getattr(llm_request, "images", None):
            return False
        if not client.ensure_connected():
            return False

        thread = threading.Thread(
            target=self._stream_daemon_request,
            args=(
                client,
                prompt,
                llm_request,
                action,
                request_id,
                search_hints,
                conversation_id,
                node_id,
                enable_consciousness,
            ),
            daemon=True,
        )
        thread.start()
        return True

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
        state = _DaemonStreamState()
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

        visible_parts = self._extract_visible_daemon_text(
            chunk.get("message", "") or "",
            state,
        )
        if bool(chunk.get("is_end_of_message", False)):
            self._finish_daemon_thinking(state)

        if visible_parts:
            self._emit_visible_daemon_parts(
                visible_parts,
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
            cleaned_part = strip_thinking_tags(part)
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
                    self._append_daemon_thinking(state, before_close)
                    self._finish_daemon_thinking(state)
                    remaining = after_close
                    continue
                self._append_daemon_thinking(state, remaining)
                break

            found_open, tag_format, before_open, after_open = (
                detect_thinking_open_tag(remaining)
            )
            if not found_open:
                visible_parts.append(remaining)
                break
            if before_open:
                visible_parts.append(before_open)
            self._start_daemon_thinking(state, tag_format)
            remaining = after_open
        return visible_parts

    def _start_daemon_thinking(
        self,
        state: _DaemonStreamState,
        tag_format: str,
    ) -> None:
        """Mark one daemon stream as being inside a thinking block."""
        state.in_thinking_block = True
        state.thinking_tag_format = tag_format
        state.thinking_content = []
        self.send_llm_thinking_signal("started", "")

    def _append_daemon_thinking(
        self,
        state: _DaemonStreamState,
        content: str,
    ) -> None:
        """Accumulate one thinking fragment and mirror it to the UI."""
        if not content:
            return
        state.thinking_content.append(content)
        self.send_llm_thinking_signal("streaming", content)

    def _finish_daemon_thinking(self, state: _DaemonStreamState) -> None:
        """Complete one thinking block if the daemon stream is inside one."""
        if not state.in_thinking_block:
            return
        self.send_llm_thinking_signal(
            "completed",
            "".join(state.thinking_content),
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
        api = getattr(self, "api", None)
        if api is None:
            api = self._resolve_api_instance()
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
        )
        usage = chunk.get("usage") or {}
        response.prompt_tokens = usage.get("prompt_tokens")
        response.completion_tokens = usage.get("completion_tokens")
        response.total_tokens = usage.get("total_tokens")
        return response
