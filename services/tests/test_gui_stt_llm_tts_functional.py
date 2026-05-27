"""Offscreen GUI functional STT + LLM + TTS coverage."""

from __future__ import annotations

import os

os.environ.setdefault("AIRUNNER_TEST_NO_GUI_LAUNCH", "1")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import shutil
import socket
import threading
import time
from pathlib import Path
from types import SimpleNamespace

import pytest
from PySide6.QtWidgets import QApplication

from llm_functional_support import BUNDLED_REFERENCE_SPEAKER
from llm_functional_support import combined_llama_env_overrides
from llm_functional_support import daemon_env
from llm_functional_support import daemon_output
from llm_functional_support import llm_artifact_path
from llm_functional_support import post_json
from llm_functional_support import started_daemon
from llm_functional_support import tts_model_path
from llm_functional_support import visible_digits
from llm_functional_support import wait_for_log_text
from test_gui_llm_tts_functional import _FakeSoundDeviceManager
from test_gui_llm_tts_functional import _MODEL_ID
from test_gui_llm_tts_functional import _clear_settings_cache
from test_gui_llm_tts_functional import _configure_test_database
from test_gui_llm_tts_functional import _daemon_client_config
from test_gui_llm_tts_functional import _seed_gui_settings
from test_gui_llm_tts_functional import _stop_worker
from test_gui_llm_tts_functional import _wait_until

from airunner.api.api_bridge import APIBridge
from airunner.api.signal_api_adapter import SignalAPIAdapter
from airunner.components.application.gui.windows.main.worker_manager import (
    WorkerManager,
)
from airunner.components.chat.gui.widgets.chat_prompt_widget import (
    ChatPromptWidget,
)
from airunner.components.llm.api.llm_services import LLMAPIService
from airunner.components.tts.workers import (
    tts_vocalizer_worker as tts_vocalizer_module,
)
from airunner.components.tts.workers.tts_vocalizer_worker import (
    TTSVocalizerWorker,
)
from airunner.daemon_client.gui_daemon_client import GuiDaemonClient
from airunner.enums import SignalCode
from airunner.utils.application.create_worker import create_worker
from airunner.utils.application.signal_mediator import SignalMediator
from airunner_model.models.application_settings import ApplicationSettings
from airunner_model.runtimes.whisper_cpp_runtime_settings import (
    resolve_whisper_cpp_runtime_settings,
)
from airunner_services.workers.tts_generator_worker import (
    TTSGeneratorWorker,
)


def _free_tcp_port() -> int:
    """Return one free local TCP port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _executable_exists(executable: str) -> bool:
    """Return whether one runtime executable is available locally."""
    candidate = Path(executable).expanduser()
    if candidate.is_file():
        return True
    return shutil.which(executable) is not None


@pytest.fixture(scope="session")
def qapp():
    try:
        app = QApplication.instance() or QApplication([])
    except Exception as exc:  # pragma: no cover - environment guard
        pytest.skip(f"PySide6 unavailable: {exc}")
    yield app


@pytest.mark.gui
@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.timeout(1200)
def test_gui_stt_llm_and_tts_round_trip_without_audio_output(
    qapp: QApplication,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Transcribe bundled audio, generate one reply, and vocalize it."""
    if not BUNDLED_REFERENCE_SPEAKER.is_file():
        pytest.fail(f"Missing bundled audio fixture: {BUNDLED_REFERENCE_SPEAKER}")

    artifact_path = llm_artifact_path(_MODEL_ID)
    if not artifact_path.is_file():
        pytest.skip(f"Missing local model artifact: {artifact_path}")

    openvoice_path = tts_model_path()
    if not openvoice_path.is_dir():
        pytest.skip(f"Real OpenVoice assets are required at {openvoice_path}")

    whisper_settings = resolve_whisper_cpp_runtime_settings()
    if not whisper_settings.model_path:
        pytest.skip(
            "Real whisper.cpp model required; set AIRUNNER_WHISPER_MODEL_PATH "
            "or install one under ~/.local/share/airunner/text/models/stt"
        )

    whisper_model_path = Path(whisper_settings.model_path).expanduser().resolve()
    if not whisper_model_path.is_file():
        pytest.skip(f"Configured whisper.cpp model is missing: {whisper_model_path}")

    if not _executable_exists(whisper_settings.executable):
        pytest.skip(
            "whisper-server executable required; set "
            "AIRUNNER_WHISPER_SERVER_BIN or AIRUNNER_BUNDLE_ROOT"
        )

    db_url = _configure_test_database(monkeypatch, tmp_path)
    _seed_gui_settings(_MODEL_ID, openvoice_path)
    app_settings = ApplicationSettings.objects.first()
    ApplicationSettings.objects.update(
        pk=getattr(app_settings, "id", None),
        llm_enabled=True,
        stt_enabled=True,
        tts_enabled=True,
    )
    _clear_settings_cache()

    fake_audio = _FakeSoundDeviceManager()
    visible_chunks: list[str] = []
    system_messages: list[str] = []
    transcriptions: list[str] = []
    response_done = threading.Event()
    transcription_done = threading.Event()
    tts_stream_done = threading.Event()
    tts_generate_done = threading.Event()
    tts_daemon_generate_done = threading.Event()

    previous_qt_api = getattr(qapp, "api", None)
    previous_main_window = getattr(qapp, "main_window", None)

    worker_manager = None
    widget = None
    mediator = SignalMediator()

    def on_stream(data: dict) -> None:
        response = data.get("response")
        if response is None:
            return
        message = str(getattr(response, "message", "") or "")
        if getattr(response, "is_system_message", False):
            if message:
                system_messages.append(message)
            if getattr(response, "is_end_of_message", False):
                response_done.set()
            return
        if message:
            visible_chunks.append(message)
        if getattr(response, "is_end_of_message", False):
            response_done.set()

    def on_transcription(data: dict) -> None:
        transcription = str(data.get("transcription", "") or "").strip()
        if not transcription:
            return
        transcriptions.append(transcription)
        transcription_done.set()

    monkeypatch.setattr(
        tts_vocalizer_module.sd,
        "query_devices",
        lambda *_args, **_kwargs: {"default_samplerate": 24000},
    )

    try:
        with started_daemon(
            daemon_env(
                llm_on=True,
                tts_on=True,
                openvoice_model_path=openvoice_path,
                extra_env={
                    **combined_llama_env_overrides(_MODEL_ID),
                    "AIRUNNER_DATABASE_URL": db_url,
                    "AIRUNNER_DISABLE_DB_SETUP_CACHE": "1",
                    "AIRUNNER_DISABLE_ALWAYS_TOOLS": "1",
                    "AIRUNNER_STT_ON": "1",
                    "AIRUNNER_WHISPER_MODEL_PATH": str(whisper_model_path),
                    "AIRUNNER_WHISPER_HOST": "127.0.0.1",
                    "AIRUNNER_WHISPER_PORT": str(_free_tcp_port()),
                    "AIRUNNER_WHISPER_STARTUP_TIMEOUT": "120",
                },
            )
        ) as daemon:
            load_status, load_body, _ = post_json(
                f"{daemon.base_url}/api/v1/daemon/runtimes/stt/load",
                {
                    "provider": "local",
                    "deployment_mode": "sidecar",
                    "request_id": "functional-gui-stt-load",
                },
                timeout_seconds=180.0,
            )

            assert load_status == 200, daemon_output(daemon.log_path)
            assert "succeeded" in load_body.decode("utf-8"), daemon_output(
                daemon.log_path
            )

            api = SimpleNamespace(
                headless=False,
                daemon_client=GuiDaemonClient(
                    config_path=_daemon_client_config(tmp_path, daemon.port)
                ),
                sounddevice_manager=fake_audio,
                model_load_balancer=SimpleNamespace(
                    get_loaded_models=lambda: [],
                    switch_to_non_art_mode=lambda: None,
                ),
                current_conversation_id=None,
            )
            api.api_bridge = APIBridge(
                api.daemon_client,
                signal_emitter=mediator.emit_signal,
            )
            api.api_adapter = SignalAPIAdapter(
                api.api_bridge,
                emit_signal=mediator.emit_signal,
            )
            qapp.api = api

            worker_manager = create_worker(
                WorkerManager,
                signal_api_adapter=api.api_adapter,
            )
            main_window = SimpleNamespace(worker_manager=worker_manager, api=api)
            api.main_window = main_window
            api.app = SimpleNamespace(main_window=main_window, api=api)
            qapp.main_window = main_window

            api.llm = LLMAPIService()
            api.llm.api = api

            real_send_request = api.llm.send_request

            def send_request_with_functional_overrides(
                prompt: str,
                **kwargs,
            ) -> None:
                llm_request = kwargs.get("llm_request")
                if llm_request is not None:
                    llm_request.system_prompt = (
                        "No matter what the user says, reply with exactly "
                        "the single digit 7."
                    )
                    llm_request.enable_thinking = False
                    llm_request.do_sample = False
                    llm_request.top_p = 0.1
                    llm_request.temperature = 0.1
                    llm_request.max_new_tokens = 16
                    llm_request.use_memory = False
                    llm_request.ephemeral = True
                    llm_request.ephemeral_conversation = True
                    llm_request.tool_categories = None
                real_send_request(prompt, **kwargs)

            api.llm.send_request = send_request_with_functional_overrides
            worker_manager.api = api
            worker_manager._stream_tts_worker = (
                lambda: worker_manager.tts_generator_worker
            )
            api.llm._tts_stream_worker = (
                lambda: worker_manager.tts_generator_worker
            )

            real_on_llm_text_streamed_signal = (
                TTSGeneratorWorker.on_llm_text_streamed_signal
            )
            real_generate = TTSGeneratorWorker._generate
            real_generate_via_daemon = TTSGeneratorWorker._generate_via_daemon

            def on_llm_text_streamed_signal_probe(_self, data):
                tts_stream_done.set()
                return real_on_llm_text_streamed_signal(_self, data)

            def generate_probe(_self, message):
                tts_generate_done.set()
                return real_generate(_self, message)

            def generate_via_daemon_probe(_self, message, model_type):
                tts_daemon_generate_done.set()
                return real_generate_via_daemon(_self, message, model_type)

            monkeypatch.setattr(
                TTSGeneratorWorker,
                "on_llm_text_streamed_signal",
                on_llm_text_streamed_signal_probe,
            )
            monkeypatch.setattr(
                TTSGeneratorWorker,
                "tts_enabled",
                property(lambda _self: True),
            )
            monkeypatch.setattr(TTSGeneratorWorker, "_generate", generate_probe)
            monkeypatch.setattr(
                TTSGeneratorWorker,
                "_generate_via_daemon",
                generate_via_daemon_probe,
            )
            monkeypatch.setattr(
                TTSGeneratorWorker,
                "_daemon_client",
                lambda _self: api.daemon_client,
            )
            monkeypatch.setattr(
                TTSVocalizerWorker,
                "_sounddevice_manager",
                lambda _self: fake_audio,
            )

            mediator.register(SignalCode.LLM_TEXT_STREAMED_SIGNAL, on_stream)
            mediator.register(
                SignalCode.AUDIO_PROCESSOR_RESPONSE_SIGNAL,
                on_transcription,
            )

            widget = ChatPromptWidget()
            widget.api = api
            widget.show()
            qapp.processEvents()

            mediator.emit_signal(
                SignalCode.AUDIO_CAPTURE_WORKER_RESPONSE_SIGNAL,
                {
                    "audio_bytes": BUNDLED_REFERENCE_SPEAKER.read_bytes(),
                    "mime_type": "audio/wav",
                },
            )

            _wait_until(
                qapp,
                transcription_done.is_set,
                timeout_seconds=600,
                message=(
                    "Timed out waiting for GUI STT transcription.\n"
                    f"{daemon_output(daemon.log_path)}"
                ),
            )

            _wait_until(
                qapp,
                response_done.is_set,
                timeout_seconds=600,
                message=(
                    "Timed out waiting for GUI response stream.\n"
                    f"{daemon_output(daemon.log_path)}"
                ),
            )

            assert transcriptions
            assert transcriptions[-1].strip()
            assert not system_messages, system_messages
            assert visible_digits("".join(visible_chunks)) == "7"

            _wait_until(
                qapp,
                tts_stream_done.is_set,
                timeout_seconds=30,
                message=(
                    "Timed out waiting for GUI TTS stream handoff.\n"
                    f"{daemon_output(daemon.log_path)}"
                ),
            )
            _wait_until(
                qapp,
                tts_generate_done.is_set,
                timeout_seconds=30,
                message=(
                    "Timed out waiting for GUI TTS generation.\n"
                    f"{daemon_output(daemon.log_path)}"
                ),
            )
            _wait_until(
                qapp,
                tts_daemon_generate_done.is_set,
                timeout_seconds=30,
                message=(
                    "Timed out waiting for GUI daemon-backed TTS synth.\n"
                    f"{daemon_output(daemon.log_path)}"
                ),
            )
            _wait_until(
                qapp,
                fake_audio.write_event.is_set,
                timeout_seconds=180,
                message=(
                    "Timed out waiting for GUI playback write.\n"
                    f"{daemon_output(daemon.log_path)}"
                ),
            )

            assert fake_audio.initialize_calls
            assert fake_audio.write_calls
            assert fake_audio.write_calls[-1].size > 0

            wait_for_log_text(
                daemon.log_path,
                "STT request received",
                timeout_seconds=180.0,
            )
            wait_for_log_text(
                daemon.log_path,
                "TTS request received",
                timeout_seconds=180.0,
            )
    finally:
        mediator.unregister(SignalCode.LLM_TEXT_STREAMED_SIGNAL, on_stream)
        mediator.unregister(
            SignalCode.AUDIO_PROCESSOR_RESPONSE_SIGNAL,
            on_transcription,
        )
        if widget is not None:
            _stop_worker(getattr(widget, "_llm_response_worker", None))
            widget.close()
        if worker_manager is not None:
            _stop_worker(getattr(worker_manager, "_tts_generator_worker", None))
            _stop_worker(getattr(worker_manager, "_tts_vocalizer_worker", None))
            _stop_worker(getattr(worker_manager, "_model_scanner_worker", None))
            _stop_worker(worker_manager)
        qapp.processEvents()
        qapp.api = previous_qt_api
        qapp.main_window = previous_main_window
        _clear_settings_cache()