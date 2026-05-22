"""Streaming control helpers for node functions."""

from typing import Any, Dict, Optional

from langchain_core.messages import AIMessage

from airunner.enums import SignalCode


class StreamingControlMixin:
    """Wrap streaming calls and thinking-signal completion."""

    def _emit_final_thinking_signal(
        self,
        response_message: Optional[AIMessage],
    ) -> None:
        """Ensure the live thinking widget receives one final completion."""
        emitter = getattr(self, "_signal_emitter", None)
        request_id = getattr(self, "_current_request_id", None)
        if emitter is None or not request_id or response_message is None:
            return

        additional_kwargs = (
            getattr(response_message, "additional_kwargs", {}) or {}
        )
        thinking_content = (
            additional_kwargs.get("thinking_content")
            or additional_kwargs.get("reasoning_content")
            or ""
        )
        thinking_metadata = additional_kwargs.get("thinking_metadata")
        emitter.emit_signal(
            SignalCode.LLM_THINKING_SIGNAL,
            {
                "status": "completed",
                "content": str(thinking_content),
                "request_id": request_id,
                "metadata": thinking_metadata,
            },
        )

    def _stream_model_response(
        self,
        prompt: Any,
        generation_kwargs: Optional[Dict] = None,
        thinking_metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[AIMessage]:
        """Stream a response with tool mode temporarily disabled."""
        if generation_kwargs is None:
            generation_kwargs = {}

        chat_model = getattr(self, "_chat_model", None)
        if chat_model is None:
            return None

        tools_backup = getattr(chat_model, "tools", None)
        mode_backup = getattr(chat_model, "tool_calling_mode", None)
        json_mode_backup = getattr(chat_model, "use_json_mode", None)

        try:
            if hasattr(chat_model, "tools"):
                chat_model.tools = None
            try:
                if hasattr(chat_model, "tool_calling_mode"):
                    chat_model.tool_calling_mode = "react"
            except AttributeError:
                pass
            if hasattr(chat_model, "use_json_mode"):
                chat_model.use_json_mode = False

            return self._generate_streaming_response(
                prompt,
                generation_kwargs,
                thinking_metadata=thinking_metadata,
            )
        finally:
            if hasattr(chat_model, "tools"):
                chat_model.tools = tools_backup
            try:
                if hasattr(chat_model, "tool_calling_mode"):
                    chat_model.tool_calling_mode = mode_backup
            except AttributeError:
                pass
            if hasattr(chat_model, "use_json_mode"):
                chat_model.use_json_mode = json_mode_backup

    def _stream_internal_response(
        self,
        formatted_prompt: Any,
        generation_kwargs: Optional[Dict] = None,
        *,
        thinking_metadata: Optional[Dict[str, Any]] = None,
        buffer_visible_output: bool = False,
        disable_thinking: bool = False,
    ) -> Optional[AIMessage]:
        """Stream one internal model pass with tools disabled."""
        chat_model = getattr(self, "_chat_model", None)
        token_callback_backup = getattr(self, "_token_callback", None)
        if chat_model is None:
            return self._stream_model_response(
                formatted_prompt,
                generation_kwargs or {},
                thinking_metadata=thinking_metadata,
            )

        original_values = {}
        for attr_name, override in (
            ("tools", None),
            ("tool_choice", None),
        ):
            if hasattr(chat_model, attr_name):
                original_values[attr_name] = getattr(chat_model, attr_name)
                setattr(chat_model, attr_name, override)
        if disable_thinking and hasattr(chat_model, "enable_thinking"):
            original_values["enable_thinking"] = getattr(
                chat_model,
                "enable_thinking",
            )
            setattr(chat_model, "enable_thinking", False)

        try:
            if buffer_visible_output:
                self._token_callback = None
            response_message = self._stream_model_response(
                formatted_prompt,
                generation_kwargs or {},
                thinking_metadata=thinking_metadata,
            )
            if disable_thinking and response_message is not None:
                additional_kwargs = dict(
                    getattr(response_message, "additional_kwargs", {}) or {}
                )
                additional_kwargs.pop("thinking_content", None)
                additional_kwargs.pop("reasoning_content", None)
                response_message = AIMessage(
                    content=getattr(response_message, "content", "") or "",
                    additional_kwargs=additional_kwargs,
                    tool_calls=getattr(response_message, "tool_calls", []) or [],
                )
            return response_message
        finally:
            self._token_callback = token_callback_backup
            for attr_name, original_value in original_values.items():
                try:
                    setattr(chat_model, attr_name, original_value)
                except Exception:
                    self.logger.debug(
                        "Failed to restore chat model attribute %s",
                        attr_name,
                    )