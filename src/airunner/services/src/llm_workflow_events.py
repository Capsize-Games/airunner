"""Service-side event sinks for LLM workflow orchestration."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from airunner_services.contract_enums import SignalCode


@runtime_checkable
class LLMWorkflowEventSink(Protocol):
    """Protocol for workflow progress and tool-status event sinks."""

    active: bool

    def emit_tool_status(self, payload: dict[str, Any]) -> None:
        """Publish one tool-status payload."""

    def emit_thinking(self, payload: dict[str, Any]) -> None:
        """Publish one thinking-status payload."""

    def emit_bot_mood(self, payload: dict[str, Any]) -> None:
        """Publish one bot-mood payload."""


@runtime_checkable
class LLMToolActionHandler(Protocol):
    """Protocol for service-owned tool side effects."""

    active: bool

    def handle_action(
        self,
        action: str,
        payload: dict[str, Any],
    ) -> bool:
        """Handle one tool action payload."""


class NullLLMWorkflowEventSink:
    """No-op sink used for service-only workflow execution."""

    active = False

    def emit_tool_status(self, payload: dict[str, Any]) -> None:
        """Ignore one tool-status payload."""
        del payload

    def emit_thinking(self, payload: dict[str, Any]) -> None:
        """Ignore one thinking-status payload."""
        del payload

    def emit_bot_mood(self, payload: dict[str, Any]) -> None:
        """Ignore one bot-mood payload."""
        del payload


class NullLLMToolActionHandler:
    """No-op handler used when tool side effects are unavailable."""

    active = False

    def handle_action(
        self,
        action: str,
        payload: dict[str, Any],
    ) -> bool:
        """Ignore one tool action payload."""
        del action
        del payload
        return False


class MediatorSignalLLMWorkflowEventSink:
    """Adapter that forwards workflow events into the mediator signal path."""

    active = True

    def __init__(self, signal_emitter: Any) -> None:
        """Store the signal emitter used by the compatibility adapter."""
        self._signal_emitter = signal_emitter

    def emit_tool_status(self, payload: dict[str, Any]) -> None:
        """Forward one tool-status payload through the mediator."""
        self._emit(SignalCode.LLM_TOOL_STATUS_SIGNAL, payload)

    def emit_thinking(self, payload: dict[str, Any]) -> None:
        """Forward one thinking-status payload through the mediator."""
        self._emit(SignalCode.LLM_THINKING_SIGNAL, payload)

    def emit_bot_mood(self, payload: dict[str, Any]) -> None:
        """Forward one bot-mood payload through the mediator."""
        self._emit(SignalCode.BOT_MOOD_UPDATED, payload)

    def _emit(self, code: SignalCode, payload: dict[str, Any]) -> None:
        """Emit one mediator payload when the emitter supports it."""
        emit_signal = getattr(self._signal_emitter, "emit_signal", None)
        if callable(emit_signal):
            emit_signal(code, payload)


_TOOL_ACTION_SIGNAL_CODES = {
    "agent_action_proposal": SignalCode.AGENT_ACTION_PROPOSAL_SIGNAL,
    "bot_mood_updated": SignalCode.BOT_MOOD_UPDATED,
    "clear_canvas": SignalCode.CANVAS_CLEAR_LINES_SIGNAL,
    "clear_conversation": SignalCode.LLM_CLEAR_HISTORY_SIGNAL,
    "conversation_deleted": SignalCode.CONVERSATION_DELETED,
    "conversation_title_updated": SignalCode.CONVERSATION_TITLE_UPDATED,
    "generate_image": SignalCode.SD_GENERATE_IMAGE_SIGNAL,
    "load_conversation": SignalCode.LOAD_CONVERSATION_SIGNAL,
    "load_image_from_path": SignalCode.CANVAS_LOAD_IMAGE_FROM_PATH_SIGNAL,
    "new_conversation": SignalCode.NEW_CONVERSATION_SIGNAL,
    "open_code_editor": SignalCode.OPEN_CODE_EDITOR,
    "quit_application": SignalCode.APPLICATION_QUIT_SIGNAL,
    "request_user_input": SignalCode.REQUEST_USER_INPUT_SIGNAL,
    "schedule_task": SignalCode.SCHEDULE_TASK_SIGNAL,
    "set_application_mode": SignalCode.SET_APPLICATION_MODE_SIGNAL,
    "toggle_tts": SignalCode.TOGGLE_TTS_SIGNAL,
}


class MediatorSignalLLMToolActionHandler:
    """Adapter that forwards tool actions into the mediator signal path."""

    active = True

    def __init__(self, signal_emitter: Any) -> None:
        """Store one compatibility emitter for tool actions."""
        self._signal_emitter = signal_emitter

    def handle_action(
        self,
        action: str,
        payload: dict[str, Any],
    ) -> bool:
        """Map one tool action to the compatibility signal path."""
        emit_signal = getattr(self._signal_emitter, "emit_signal", None)
        if not callable(emit_signal):
            return False

        signal_code, signal_payload = self._resolve_signal(action, payload)
        if signal_code is None:
            return False

        emit_signal(signal_code, signal_payload)
        return True

    def _resolve_signal(
        self,
        action: str,
        payload: dict[str, Any],
    ) -> tuple[SignalCode | None, dict[str, Any]]:
        """Resolve one tool action into a signal payload pair."""
        if action == "emit_signal":
            return self._legacy_signal(payload)
        return _TOOL_ACTION_SIGNAL_CODES.get(action), payload

    @staticmethod
    def _legacy_signal(
        payload: dict[str, Any],
    ) -> tuple[SignalCode | None, dict[str, Any]]:
        """Resolve one legacy signal action payload."""
        signal_name = str(payload.get("signal_name", "")).strip()
        if not signal_name:
            return None, payload

        try:
            signal_code = SignalCode[signal_name]
        except KeyError:
            return None, payload

        data = payload.get("data")
        if isinstance(data, dict):
            return signal_code, data
        return signal_code, {}


def build_llm_workflow_event_sink(
    *,
    event_sink: LLMWorkflowEventSink | None = None,
    signal_emitter: Any = None,
) -> LLMWorkflowEventSink:
    """Return one concrete workflow event sink."""
    if event_sink is not None:
        return event_sink
    emit_signal = getattr(signal_emitter, "emit_signal", None)
    if callable(emit_signal):
        return MediatorSignalLLMWorkflowEventSink(signal_emitter)
    return NullLLMWorkflowEventSink()


def build_llm_tool_action_handler(
    *,
    action_handler: LLMToolActionHandler | None = None,
    signal_emitter: Any = None,
) -> LLMToolActionHandler:
    """Return one concrete tool action handler."""
    if action_handler is not None:
        return action_handler
    emit_signal = getattr(signal_emitter, "emit_signal", None)
    if callable(emit_signal):
        return MediatorSignalLLMToolActionHandler(signal_emitter)
    return NullLLMToolActionHandler()


def resolve_llm_workflow_event_sink(owner: Any) -> LLMWorkflowEventSink:
    """Resolve one workflow event sink from an owner instance."""
    signal_emitter = getattr(owner, "_signal_emitter", None)
    if signal_emitter is None and callable(getattr(owner, "emit_signal", None)):
        signal_emitter = owner
    return build_llm_workflow_event_sink(
        event_sink=getattr(owner, "_event_sink", None),
        signal_emitter=signal_emitter,
    )


def resolve_llm_tool_action_handler(owner: Any) -> LLMToolActionHandler:
    """Resolve one tool action handler from an owner instance."""
    return build_llm_tool_action_handler(
        action_handler=getattr(owner, "_tool_action_handler", None),
    )
