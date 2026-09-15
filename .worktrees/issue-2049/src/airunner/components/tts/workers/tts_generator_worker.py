"""GUI-owned streamed TTS worker backed by the daemon runtime."""

from __future__ import annotations

import io
import threading
import unicodedata
from typing import Iterable, Optional
from uuid import uuid4

import soundfile as sf

from airunner.components.application.workers.worker import Worker
from airunner.components.llm.utils.thinking_parser import (
    normalize_thinking_content,
    strip_stored_thinking_prefix,
    strip_thinking_tags,
)
from airunner.enums import LLMActionType, SignalCode
from airunner.utils.text.formatter_extended import FormatterExtended


_NO_SPACE_BEFORE = frozenset(".,!?;:%)]}>/\\")
_OPENING_CHARS = frozenset("([{</\\")
_WORD_CONTINUATION = frozenset("_")
_WORD_ENDERS = frozenset(")]}'\"")
_SENTENCE_ENDERS = frozenset(".!?;:")


def _is_space_separated_symbol(char: str) -> bool:
    """Return whether one symbol should be separated in streamed text."""
    if not char:
        return False
    if char in _NO_SPACE_BEFORE or char in _OPENING_CHARS:
        return False
    return unicodedata.category(char) == "So"


def _needs_stream_space(existing: str, chunk: str) -> bool:
    """Return whether one chunk boundary needs an inserted space."""
    if not existing or not chunk:
        return False
    prev = existing[-1]
    next_char = chunk[0]
    if prev.isspace() or next_char.isspace():
        return False
    if next_char in _NO_SPACE_BEFORE or prev in _OPENING_CHARS:
        return False

    prev_is_word = prev.isalnum() or prev in _WORD_CONTINUATION
    prev_is_word = prev_is_word or prev in _WORD_ENDERS
    next_is_word = next_char.isalnum() or next_char in _WORD_CONTINUATION
    prev_is_symbol = _is_space_separated_symbol(prev)
    next_is_symbol = _is_space_separated_symbol(next_char)

    if (prev_is_word or prev_is_symbol) and (
        next_is_word or next_is_symbol
    ):
        return True
    if prev in _SENTENCE_ENDERS and (next_is_word or next_is_symbol):
        return True
    return False


def _combine_stream_chunks(chunks: Iterable[str]) -> str:
    """Combine streamed chunks into one readable string."""
    combined = ""
    for chunk in chunks:
        if not chunk:
            continue
        if _needs_stream_space(combined, chunk):
            combined += f" {chunk}"
            continue
        combined += chunk
    return combined


class TTSGeneratorWorker(Worker):
    """Convert GUI LLM stream updates into daemon-backed TTS playback."""

    def __init__(self, *args, **kwargs):
        self.do_interrupt = False
        self._active_request_id: Optional[str] = None
        self._reset_llm_stream_state()
        super().__init__(*args, **kwargs)

    def _reset_llm_stream_state(self) -> None:
        """Clear the per-response visible/thinking tracking state."""
        self._llm_request_id = None
        self._llm_raw_visible_chunks: list[str] = []
        self._llm_spoken_visible_text = ""
        self._llm_thinking_active = False
        self._llm_thinking_content = None

    def _sync_llm_stream_state(
        self,
        request_id: Optional[str],
        *,
        is_first_message: bool = False,
    ) -> None:
        """Reset stream state when a new LLM response begins."""
        current_request_id = getattr(self, "_llm_request_id", None)
        same_request = bool(request_id) and request_id == current_request_id
        if (
            request_id
            and current_request_id
            and request_id != current_request_id
        ) or (is_first_message and not same_request):
            self._reset_llm_stream_state()
            current_request_id = None
        if request_id and current_request_id is None:
            self._llm_request_id = request_id

    def _current_visible_tts_text(self) -> str:
        """Return the visible reply text buffered for speech."""
        if self._llm_thinking_active:
            return ""
        return strip_stored_thinking_prefix(
            _combine_stream_chunks(self._llm_raw_visible_chunks),
            self._llm_thinking_content,
        )

    @property
    def tts_enabled(self) -> bool:
        """Return whether streamed GUI TTS is enabled."""
        settings = getattr(self, "application_settings", None)
        return bool(getattr(settings, "tts_enabled", False))

    def _current_api(self):
        """Return the freshest API reference available."""
        refresher = getattr(self, "refresh_api_reference", None)
        if callable(refresher):
            api = refresher()
            if api is not None:
                return api
        api = getattr(self, "api", None)
        if api is not None:
            return api
        return None

    def _daemon_client(self):
        """Return the GUI daemon client when it is available."""
        api = self._current_api()
        if api is None:
            return None
        return getattr(api, "daemon_client", None)

    def _active_tts_model(self) -> Optional[str]:
        """Return the currently selected TTS model name."""
        model = getattr(self.chatbot_voice_settings, "model_type", None)
        return getattr(model, "value", model)

    def _generate_daemon_visible_reply_async(self, message: str) -> None:
        """Generate one daemon-backed reply without blocking the worker."""
        threading.Thread(
            target=self._generate,
            args=(message,),
            daemon=True,
        ).start()

    def on_llm_thinking_signal(self, data: Optional[dict]) -> None:
        """Track the active reasoning stream so TTS speaks final text only."""
        if not isinstance(data, dict):
            return
        self._sync_llm_stream_state(data.get("request_id"))

        status = str(data.get("status", "")).strip().lower()
        if status == "started":
            self._llm_thinking_active = True
            self._llm_thinking_content = None
            return
        if status == "streaming":
            self._llm_thinking_active = True
            return
        if status == "completed":
            self._llm_thinking_active = False
            self._llm_thinking_content = normalize_thinking_content(
                data.get("content")
            )

    def on_llm_text_streamed_signal(self, data: dict) -> None:
        """Queue one streamed LLM reply for daemon-backed speech."""
        if not self.tts_enabled or not isinstance(data, dict):
            return

        response = data.get("response")
        if response is None:
            return
        if getattr(response, "action", None) is LLMActionType.GENERATE_IMAGE:
            return
        if getattr(response, "is_system_message", False):
            return

        self._sync_llm_stream_state(
            getattr(response, "request_id", None),
            is_first_message=bool(
                getattr(response, "is_first_message", False)
            ),
        )

        cleaned_message = strip_thinking_tags(
            getattr(response, "message", "") or ""
        ).replace("</s>", "")
        if cleaned_message:
            self._llm_raw_visible_chunks.append(cleaned_message)

        if self.do_interrupt:
            self.on_unblock_tts_generator_signal(None)

        if not getattr(response, "is_end_of_message", False):
            return

        final_message = self._current_visible_tts_text().strip()
        if final_message:
            if final_message[-1] not in ".!?":
                final_message += "."
            self._generate_daemon_visible_reply_async(final_message)
        self._reset_llm_stream_state()

    def on_interrupt_process_signal(self, data: Optional[dict] = None) -> None:
        """Cancel one active daemon TTS request and clear buffered state."""
        del data
        client = self._daemon_client()
        request_id = self._active_request_id
        if client is not None and request_id is not None:
            try:
                client.cancel_runtime(
                    "tts",
                    deployment_mode="sidecar",
                    request_id=request_id,
                    auto_start=False,
                )
            except RuntimeError:
                pass
            self._active_request_id = None
        self.empty_queue()
        self.do_interrupt = True
        self.paused = True
        self._reset_llm_stream_state()

    def on_unblock_tts_generator_signal(
        self,
        data: Optional[dict],
    ) -> None:
        """Allow new streamed TTS work after one interruption."""
        if self.tts_enabled:
            self.do_interrupt = False
            self.paused = False
        if data is None:
            return
        callback = data.get("callback")
        if callable(callback):
            callback()

    def on_application_settings_changed_signal(self, data: Optional[dict]):
        """GUI daemon TTS reload is handled by WorkerManager."""
        del data

    @staticmethod
    def _decode_daemon_audio(audio_bytes: bytes):
        """Decode one daemon audio payload into mono float32 audio."""
        audio, _sample_rate = sf.read(io.BytesIO(audio_bytes), dtype="float32")
        if getattr(audio, "ndim", 1) > 1:
            return audio[:, 0]
        return audio

    def _generate_via_daemon(
        self,
        message: str,
        model_type: Optional[str],
    ):
        """Request one synthesized TTS payload from the daemon."""
        client = self._daemon_client()
        if client is None:
            return None
        request_id = str(uuid4())
        self._active_request_id = request_id
        try:
            audio_bytes = client.synthesize_tts(
                message,
                voice=getattr(self.chatbot_voice_settings, "voice", None),
                model=getattr(self.path_settings, "tts_model_path", None),
                model_type=model_type,
                request_id=request_id,
            )
            return self._decode_daemon_audio(audio_bytes)
        except RuntimeError as exc:
            self.logger.error("Daemon TTS generation failed: %s", exc)
            return None
        finally:
            self._active_request_id = None

    def _generate(self, message) -> None:
        """Generate one daemon-backed TTS response for GUI playback."""
        if self.do_interrupt:
            return
        if isinstance(message, dict):
            message = message.get("message", "")
        message = FormatterExtended.to_speakable_text(str(message or ""))
        if not message:
            return

        response = self._generate_via_daemon(
            message,
            self._active_tts_model(),
        )
        if self.do_interrupt or response is None:
            return
        self.emit_signal(
            SignalCode.TTS_GENERATOR_WORKER_ADD_TO_STREAM_SIGNAL,
            {"message": response},
        )

    @staticmethod
    def _is_control_queue_message(message) -> bool:
        """Return whether one queued payload must bypass interrupt drops."""
        if not isinstance(message, dict):
            return False
        message_type = message.get("_message_type")
        return isinstance(message_type, str) and bool(message_type.strip())

    def add_to_queue(self, message) -> None:
        """Drop non-control messages while interrupted."""
        if self.do_interrupt and not self._is_control_queue_message(message):
            return
        super().add_to_queue(message)

    def get_item_from_queue(self):
        """Drop stale queued work while interrupted."""
        message = super().get_item_from_queue()
        if message is None:
            return None
        if self.do_interrupt and not self._is_control_queue_message(message):
            return None
        return message

    def handle_message(self, data) -> None:
        """Dispatch one worker queue payload."""
        message_type = data.get("_message_type") if data else None
        if message_type == "interrupt":
            self.on_interrupt_process_signal(data.get("data"))
            return
        if message_type == "unblock_tts_generator":
            self.on_unblock_tts_generator_signal(data.get("data"))
            return
        if message_type == "llm_text_streamed":
            self.on_llm_text_streamed_signal(data.get("data") or {})
            return
        if message_type == "llm_thinking":
            self.on_llm_thinking_signal(data.get("data") or {})
            return
        if message_type == "application_settings_changed":
            self.on_application_settings_changed_signal(
                data.get("data") or {}
            )