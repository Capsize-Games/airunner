"""Offscreen GUI functional LLM + TTS coverage using the real daemon."""

from __future__ import annotations

import os

os.environ.setdefault("AIRUNNER_TEST_NO_GUI_LAUNCH", "1")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import threading
import time
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
import yaml
from PySide6.QtWidgets import QApplication

from llm_functional_support import BUNDLED_REFERENCE_SPEAKER
from llm_functional_support import combined_llama_env_overrides
from llm_functional_support import daemon_env
from llm_functional_support import daemon_output
from llm_functional_support import llm_artifact_path
from llm_functional_support import started_daemon
from llm_functional_support import tts_model_path
from llm_functional_support import visible_digits
from llm_functional_support import wait_for_log_text

from airunner.components.application.gui.windows.main.settings_mixin_shared_instance import (
    SettingsMixinSharedInstance,
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
from airunner_model.models.chatbot import Chatbot
from airunner_model.models.llm_generator_settings import (
    LLMGeneratorSettings,
)
from airunner_model.models.openvoice_settings import OpenVoiceSettings
from airunner_model.models.path_settings import PathSettings
from airunner_model.models.voice_settings import VoiceSettings
from airunner_model.session import reset_engine
from airunner_services.setup_database import setup_database
from airunner_services.workers.tts_generator_worker import (
    TTSGeneratorWorker,
)
from airunner.components.application.gui.windows.main.worker_manager import (
    WorkerManager,
)


_MODEL_ID = "qwen3.5-9b"
_PROMPT = "/no_think\nReply with exactly the single digit 7."
_PROGRESSION_FIRST_REPLY = "marigold"
_PROGRESSION_SECOND_REPLY = f"ack{_PROGRESSION_FIRST_REPLY}"
_PROGRESSION_FIRST_PROMPT = (
    "/no_think\nReply with exactly marigold and nothing else."
)
_PROGRESSION_SECOND_PROMPT = (
    "/no_think\nReply with exactly ack followed by the exact full text "
    "of your previous answer, with no spaces and nothing else."
)


class _FakeOutputStream:
    def __init__(self, channels: int) -> None:
        self.active = True
        self.channels = channels


class _FakeSoundDeviceManager:
    def __init__(self) -> None:
        self.out_stream = None
        self.initialize_calls = []
        self.write_calls = []
        self.write_event = threading.Event()

    def initialize_output_stream(
        self,
        samplerate: int = 24000,
        channels: int = 1,
        device_name: str = "pulse",
    ) -> bool:
        self.initialize_calls.append((samplerate, channels, device_name))
        self.out_stream = _FakeOutputStream(channels)
        return True

    def write_to_output(self, data) -> bool:
        self.write_calls.append(np.array(data, copy=True))
        self.write_event.set()
        return True

    def _stop_output_stream(self) -> None:
        self.out_stream = None


def compact_visible_text(text: str) -> str:
    return "".join(text.split())


@pytest.fixture(scope="session")
def qapp():
    try:
        app = QApplication.instance() or QApplication([])
    except Exception as exc:  # pragma: no cover - environment guard
        pytest.skip(f"PySide6 unavailable: {exc}")
    yield app


def _clear_settings_cache() -> None:
    shared = SettingsMixinSharedInstance()
    shared.chatbot = None
    shared._settings_cache.clear()
    shared._settings_cache_by_key.clear()


def _configure_test_database(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> str:
    db_url = f"sqlite:///{tmp_path / 'gui-functional.sqlite'}"
    monkeypatch.setenv("AIRUNNER_DATABASE_URL", db_url)
    monkeypatch.setenv("AIRUNNER_DISABLE_DB_SETUP_CACHE", "1")
    monkeypatch.setenv("AIRUNNER_TTS_MODEL_TYPE", "OpenVoice")
    reset_engine()
    _clear_settings_cache()
    setup_database()
    return db_url


def _ensure_row(model_class, **defaults):
    instance = model_class.objects.first()
    if instance is None:
        instance = model_class.objects.create(**defaults)
    return instance or model_class.objects.first()


def _seed_gui_settings(
    model_id: str,
    openvoice_path: Path,
    *,
    tts_enabled: bool = True,
) -> None:
    artifact_path = llm_artifact_path(model_id)
    llm_settings = _ensure_row(LLMGeneratorSettings)
    LLMGeneratorSettings.objects.update(
        pk=getattr(llm_settings, "id", None),
        model_id=model_id,
        model_version=model_id,
        model_path=str(artifact_path),
        model_service="local",
        override_parameters=True,
        do_sample=False,
        top_p=100,
        temperature=100,
        repetition_penalty=115,
        top_k=20,
        max_new_tokens=16,
        ngram_size=3,
        enable_thinking=False,
    )

    app_settings = _ensure_row(ApplicationSettings)
    ApplicationSettings.objects.update(
        pk=getattr(app_settings, "id", None),
        llm_enabled=True,
        tts_enabled=tts_enabled,
    )

    path_settings = _ensure_row(PathSettings)
    PathSettings.objects.update(
        pk=getattr(path_settings, "id", None),
        tts_model_path=str(openvoice_path),
    )

    openvoice_settings = _ensure_row(OpenVoiceSettings)
    OpenVoiceSettings.objects.update(
        pk=getattr(openvoice_settings, "id", None),
        reference_speaker_path=str(BUNDLED_REFERENCE_SPEAKER),
    )
    openvoice_settings = OpenVoiceSettings.objects.first()

    chatbot = (
        Chatbot.objects.filter_by_first(current=True)
        or Chatbot.objects.first()
        or Chatbot.objects.create(name="GUI Functional Chatbot")
    )
    voice_settings = _ensure_row(
        VoiceSettings,
        name="GUI Functional Voice",
        model_type="OpenVoice",
        settings_id=getattr(openvoice_settings, "id", None),
    )
    VoiceSettings.objects.update(
        pk=getattr(voice_settings, "id", None),
        model_type="OpenVoice",
        settings_id=getattr(openvoice_settings, "id", None),
    )
    voice_settings = VoiceSettings.objects.first()
    Chatbot.objects.update(
        pk=getattr(chatbot, "id", None),
        voice_id=getattr(voice_settings, "id", None),
        current=True,
        do_sample=False,
        top_p=100,
        temperature=1000,
        repetition_penalty=115,
        top_k=20,
        max_new_tokens=16,
        ngram_size=3,
    )
    Chatbot.make_current(getattr(chatbot, "id", None))
    _clear_settings_cache()


def _daemon_client_config(tmp_path: Path, port: int) -> Path:
    config_path = tmp_path / "gui-daemon.yaml"
    config_path.write_text(
        yaml.safe_dump({"server": {"host": "127.0.0.1", "port": port}}),
        encoding="utf-8",
    )
    return config_path


def _wait_until(
    qapp: QApplication,
    predicate,
    *,
    timeout_seconds: float,
    message: str,
) -> None:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        qapp.processEvents()
        if predicate():
            return
        time.sleep(0.01)
    pytest.fail(message)


def _stop_worker(worker) -> None:
    if worker is None:
        return
    stop = getattr(worker, "stop", None)
    if callable(stop):
        stop()
    thread_getter = getattr(worker, "thread", None)
    if not callable(thread_getter):
        return
    thread = thread_getter()
    if thread is None:
        return
    quit_thread = getattr(thread, "quit", None)
    if callable(quit_thread):
        quit_thread()
    wait = getattr(thread, "wait", None)
    if callable(wait):
        wait(5000)


@pytest.mark.gui
@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.timeout(1200)
def test_gui_llm_and_tts_end_to_end_without_audio_output(
    qapp: QApplication,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    if not BUNDLED_REFERENCE_SPEAKER.is_file():
        pytest.fail(f"Missing bundled speaker: {BUNDLED_REFERENCE_SPEAKER}")

    artifact_path = llm_artifact_path(_MODEL_ID)
    if not artifact_path.is_file():
        pytest.skip(f"Missing local model artifact: {artifact_path}")

    openvoice_path = tts_model_path()
    if not openvoice_path.is_dir():
        pytest.skip(f"Real OpenVoice assets are required at {openvoice_path}")

    db_url = _configure_test_database(monkeypatch, tmp_path)
    _seed_gui_settings(_MODEL_ID, openvoice_path)

    fake_audio = _FakeSoundDeviceManager()
    visible_chunks: list[str] = []
    system_messages: list[str] = []
    response_done = threading.Event()
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
                },
            )
        ) as daemon:
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
            qapp.api = api

            worker_manager = create_worker(WorkerManager)
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
                    llm_request.system_prompt = "Reply with one character only."
                    llm_request.enable_thinking = False
                    llm_request.do_sample = False
                    llm_request.temperature = 0.1
                    llm_request.top_p = 0.1
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
            monkeypatch.setattr(
                TTSGeneratorWorker,
                "_generate",
                generate_probe,
            )
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

            widget = ChatPromptWidget()
            widget.api = api
            widget.show()
            qapp.processEvents()
            widget.do_generate(prompt_override=_PROMPT)

            _wait_until(
                qapp,
                response_done.is_set,
                timeout_seconds=600,
                message=(
                    "Timed out waiting for GUI response stream.\n"
                    f"{daemon_output(daemon.log_path)}"
                ),
            )

            assert not system_messages, system_messages
            visible_message = "".join(visible_chunks)
            assert visible_digits(visible_message) == "7", visible_message

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
                    f"daemon_generate={tts_daemon_generate_done.is_set()}\n"
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
                f"[LLM LOAD] Chat model loaded: True (model_id={_MODEL_ID}",
                timeout_seconds=60,
            )
            wait_for_log_text(
                daemon.log_path,
                "TTS request received",
                timeout_seconds=180,
            )
    finally:
        mediator.unregister(SignalCode.LLM_TEXT_STREAMED_SIGNAL, on_stream)
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
        reset_engine()
        _clear_settings_cache()


@pytest.mark.gui
@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.timeout(1200)
def test_gui_llm_conversation_progresses_without_audio_output(
    qapp: QApplication,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    if not BUNDLED_REFERENCE_SPEAKER.is_file():
        pytest.fail(f"Missing bundled speaker: {BUNDLED_REFERENCE_SPEAKER}")

    artifact_path = llm_artifact_path(_MODEL_ID)
    if not artifact_path.is_file():
        pytest.skip(f"Missing local model artifact: {artifact_path}")

    db_url = _configure_test_database(monkeypatch, tmp_path)
    _seed_gui_settings(_MODEL_ID, tts_model_path(), tts_enabled=False)

    fake_audio = _FakeSoundDeviceManager()
    visible_chunks_by_request: dict[str, list[str]] = {}
    system_messages_by_request: dict[str, list[str]] = {}
    response_done_by_request: dict[str, threading.Event] = {}
    submitted_request_ids: list[str] = []

    previous_qt_api = getattr(qapp, "api", None)
    previous_main_window = getattr(qapp, "main_window", None)

    worker_manager = None
    widget = None
    mediator = SignalMediator()

    def on_stream(data: dict) -> None:
        response = data.get("response")
        if response is None:
            return
        request_id = str(
            data.get("request_id")
            or getattr(response, "request_id", "")
            or ""
        )
        if not request_id:
            return
        visible_chunks = visible_chunks_by_request.setdefault(request_id, [])
        system_messages = system_messages_by_request.setdefault(
            request_id,
            [],
        )
        done_event = response_done_by_request.setdefault(
            request_id,
            threading.Event(),
        )
        message = str(getattr(response, "message", "") or "")
        if getattr(response, "is_system_message", False):
            if message:
                system_messages.append(message)
            if getattr(response, "is_end_of_message", False):
                done_event.set()
            return
        if message:
            visible_chunks.append(message)
        if getattr(response, "is_end_of_message", False):
            done_event.set()

    monkeypatch.setattr(
        tts_vocalizer_module.sd,
        "query_devices",
        lambda *_args, **_kwargs: {"default_samplerate": 24000},
    )

    try:
        with started_daemon(
            daemon_env(
                llm_on=True,
                tts_on=False,
                extra_env={
                    **combined_llama_env_overrides(_MODEL_ID),
                    "AIRUNNER_DATABASE_URL": db_url,
                    "AIRUNNER_DISABLE_DB_SETUP_CACHE": "1",
                    "AIRUNNER_DISABLE_ALWAYS_TOOLS": "1",
                },
            )
        ) as daemon:
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
            qapp.api = api

            worker_manager = create_worker(WorkerManager)
            main_window = SimpleNamespace(worker_manager=worker_manager, api=api)
            api.main_window = main_window
            api.app = SimpleNamespace(main_window=main_window, api=api)
            qapp.main_window = main_window

            api.llm = LLMAPIService()
            api.llm.api = api

            real_send_request = api.llm.send_request

            def send_request_with_progression_overrides(
                prompt: str,
                **kwargs,
            ) -> None:
                request_id = kwargs.get("request_id")
                if request_id is not None:
                    submitted_request_ids.append(str(request_id))
                llm_request = kwargs.get("llm_request")
                if llm_request is not None:
                    llm_request.system_prompt = (
                        "Reply with only the exact requested text."
                    )
                    llm_request.enable_thinking = False
                    llm_request.do_sample = False
                    llm_request.temperature = 0.1
                    llm_request.top_p = 0.1
                    llm_request.max_new_tokens = 32
                    llm_request.use_memory = True
                    llm_request.ephemeral = False
                    llm_request.ephemeral_conversation = False
                    llm_request.do_tts_reply = False
                    llm_request.tool_categories = []
                real_send_request(prompt, **kwargs)

            api.llm.send_request = send_request_with_progression_overrides
            worker_manager.api = api
            worker_manager._stream_tts_worker = (
                lambda: worker_manager.tts_generator_worker
            )
            api.llm._tts_stream_worker = (
                lambda: worker_manager.tts_generator_worker
            )

            monkeypatch.setattr(
                TTSGeneratorWorker,
                "tts_enabled",
                property(lambda _self: False),
            )

            mediator.register(SignalCode.LLM_TEXT_STREAMED_SIGNAL, on_stream)

            widget = ChatPromptWidget()
            widget.api = api
            widget.show()
            qapp.processEvents()

            def send_prompt_and_wait(prompt: str) -> tuple[str, str, list[str]]:
                previous_request_count = len(submitted_request_ids)
                widget.do_generate(prompt_override=prompt)
                _wait_until(
                    qapp,
                    lambda: len(submitted_request_ids) > previous_request_count,
                    timeout_seconds=30,
                    message=(
                        "Timed out waiting for GUI request submission.\n"
                        f"{daemon_output(daemon.log_path)}"
                    ),
                )
                request_id = submitted_request_ids[-1]
                _wait_until(
                    qapp,
                    lambda: request_id in response_done_by_request
                    and response_done_by_request[request_id].is_set(),
                    timeout_seconds=600,
                    message=(
                        "Timed out waiting for GUI response stream.\n"
                        f"request_id={request_id}\n"
                        f"{daemon_output(daemon.log_path)}"
                    ),
                )
                return (
                    request_id,
                    "".join(visible_chunks_by_request.get(request_id, [])),
                    system_messages_by_request.get(request_id, []),
                )

            first_request_id, first_visible_message, first_system_messages = (
                send_prompt_and_wait(_PROGRESSION_FIRST_PROMPT)
            )

            assert not first_system_messages, first_system_messages
            assert compact_visible_text(first_visible_message) == (
                _PROGRESSION_FIRST_REPLY
            )

            first_conversation_id = getattr(widget, "conversation_id", None)
            assert first_conversation_id is not None

            second_request_id, second_visible_message, second_system_messages = (
                send_prompt_and_wait(_PROGRESSION_SECOND_PROMPT)
            )

            assert second_request_id != first_request_id
            assert not second_system_messages, second_system_messages
            assert compact_visible_text(second_visible_message) == (
                _PROGRESSION_SECOND_REPLY
            )
            assert compact_visible_text(second_visible_message) != (
                compact_visible_text(first_visible_message)
            )
            assert getattr(widget, "conversation_id", None) == first_conversation_id

            wait_for_log_text(
                daemon.log_path,
                f"[LLM LOAD] Chat model loaded: True (model_id={_MODEL_ID}",
                timeout_seconds=60,
            )
    finally:
        mediator.unregister(SignalCode.LLM_TEXT_STREAMED_SIGNAL, on_stream)
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
        reset_engine()
        _clear_settings_cache()