"""Tests for daemon-backed TTS generator worker behavior."""

import queue
from types import SimpleNamespace
from unittest.mock import Mock

from airunner.enums import LLMActionType, ModelStatus, ModelType, SignalCode
from airunner.components.tts.workers.tts_generator_worker import (
    TTSGeneratorWorker,
)
from airunner.components.tts.workers.tts_vocalizer_worker import (
    TTSVocalizerWorker,
)


class FakeDaemonClient:
    """Minimal daemon client double for TTS worker tests."""

    def __init__(self):
        self.calls = []

    def synthesize_tts(self, text, **kwargs):
        self.calls.append(("synthesize", text, kwargs))
        return b"wav-bytes"

    def cancel_runtime(self, runtime_name, **kwargs):
        self.calls.append(("cancel", runtime_name, kwargs))
        return {"status": "cancelled"}


def test_generate_via_daemon_uses_tts_route_and_clears_request_id():
    client = FakeDaemonClient()
    worker = SimpleNamespace(
        _active_request_id=None,
        chatbot_voice_settings=SimpleNamespace(voice="alloy"),
        path_settings=SimpleNamespace(tts_model_path="/tmp/tts-model"),
        logger=SimpleNamespace(error=lambda *args, **kwargs: None),
        _daemon_client=lambda: client,
        _decode_daemon_audio=lambda audio_bytes: ("decoded", audio_bytes),
    )

    response = TTSGeneratorWorker._generate_via_daemon(
        worker,
        "Speak this",
        "openvoice",
    )

    assert response == ("decoded", b"wav-bytes")
    assert client.calls[0][0] == "synthesize"
    assert client.calls[0][2]["request_id"]
    assert worker._active_request_id is None


def test_interrupt_process_cancels_active_daemon_request():
    client = FakeDaemonClient()
    worker = SimpleNamespace(
        _active_request_id="tts-req-1",
        play_queue=[],
        play_queue_started=False,
        tokens=[],
        _sentence_buffer=[],
        queue=queue.Queue(),
        do_interrupt=False,
        paused=False,
        tts=None,
        _daemon_client=lambda: client,
    )

    TTSGeneratorWorker.on_interrupt_process_signal(worker)

    assert client.calls[0][0] == "cancel"
    assert client.calls[0][1] == "tts"
    assert worker.do_interrupt is True


def test_handle_message_dispatches_interrupt_requests():
    worker = SimpleNamespace(on_interrupt_process_signal=Mock())

    TTSGeneratorWorker.handle_message(
        worker,
        {"_message_type": "interrupt", "data": {"source": "test"}},
    )

    worker.on_interrupt_process_signal.assert_called_once_with(
        {"source": "test"}
    )


def test_vocalizer_handle_message_dispatches_interrupt_requests():
    worker = SimpleNamespace(on_interrupt_process_signal=Mock())

    TTSVocalizerWorker.handle_message(
        worker,
        {"_message_type": "interrupt", "data": {"source": "test"}},
    )

    worker.on_interrupt_process_signal.assert_called_once_with(
        {"source": "test"}
    )


def test_reload_tts_model_manager_handles_missing_local_handler():
    worker = SimpleNamespace(
        logger=SimpleNamespace(info=lambda *args, **kwargs: None),
        _current_model=None,
        tts=None,
        _load_tts=Mock(),
    )

    TTSGeneratorWorker._reload_tts_model_manager(
        worker,
        {"model": "OpenVoice", "voice_id": 1},
    )

    assert worker._current_model == "OpenVoice"
    assert worker.tts is None
    worker._load_tts.assert_called_once_with()


def test_reload_tts_model_manager_replaces_existing_local_handler():
    old_tts = SimpleNamespace(unload=Mock())
    worker = SimpleNamespace(
        logger=SimpleNamespace(info=lambda *args, **kwargs: None),
        _current_model="Espeak",
        tts=old_tts,
        _load_tts=Mock(),
    )

    TTSGeneratorWorker._reload_tts_model_manager(
        worker,
        {"model": "OpenVoice", "voice_id": 1},
    )

    old_tts.unload.assert_called_once_with()
    assert worker._current_model == "OpenVoice"
    assert worker.tts is None
    worker._load_tts.assert_called_once_with()


def test_unblock_tts_generator_signal_handles_missing_local_handler():
    worker = SimpleNamespace(
        tts_enabled=True,
        logger=SimpleNamespace(debug=lambda *args, **kwargs: None),
        do_interrupt=True,
        paused=True,
        tts=None,
    )

    TTSGeneratorWorker.on_unblock_tts_generator_signal(worker, None)

    assert worker.do_interrupt is False
    assert worker.paused is False


def test_daemon_client_uses_refreshed_api_reference():
    client = FakeDaemonClient()
    worker = SimpleNamespace(
        api=SimpleNamespace(headless=False),
        refresh_api_reference=Mock(
            return_value=SimpleNamespace(
                daemon_client=client,
                headless=False,
            )
        ),
    )
    worker._current_api = lambda: TTSGeneratorWorker._current_api(worker)

    assert TTSGeneratorWorker._daemon_client(worker) is client


def test_daemon_client_uses_resolved_api_reference():
    client = FakeDaemonClient()
    worker = SimpleNamespace(
        api=None,
        refresh_api_reference=Mock(return_value=None),
        _resolve_api_instance=Mock(
            return_value=SimpleNamespace(
                daemon_client=client,
                headless=False,
            )
        ),
    )
    worker._current_api = lambda: TTSGeneratorWorker._current_api(worker)

    assert TTSGeneratorWorker._daemon_client(worker) is client


def test_daemon_client_falls_back_to_main_window_worker_manager():
    client = FakeDaemonClient()
    worker = SimpleNamespace(
        api=SimpleNamespace(headless=False),
        refresh_api_reference=Mock(return_value=SimpleNamespace(headless=False)),
        _resolve_api_instance=Mock(return_value=None),
        _main_window=lambda: SimpleNamespace(
            api=SimpleNamespace(headless=False, daemon_client=None),
            daemon_client=None,
            worker_manager=SimpleNamespace(_daemon_client=lambda: client),
        ),
    )
    worker._current_api = lambda: TTSGeneratorWorker._current_api(worker)

    assert TTSGeneratorWorker._daemon_client(worker) is client


def test_streamed_text_skips_repeated_local_load_after_failure():
    worker = SimpleNamespace(
        application_settings=SimpleNamespace(tts_enabled=True),
        tts_enabled=True,
        logger=SimpleNamespace(debug=lambda *args, **kwargs: None),
        refresh_api_reference=Mock(return_value=SimpleNamespace(headless=False)),
        _failed_model="OpenVoice",
        chatbot_voice_settings=SimpleNamespace(model_type="OpenVoice"),
        tts=None,
        do_interrupt=False,
        add_to_queue=Mock(),
        _load_tts=Mock(),
        _daemon_client=lambda: None,
        _active_tts_model=lambda: "OpenVoice",
    )

    TTSGeneratorWorker.on_llm_text_streamed_signal(
        worker,
        {
            "response": SimpleNamespace(
                action=LLMActionType.CHAT,
                is_system_message=False,
                is_end_of_message=False,
                message="hello",
            )
        },
    )

    worker._load_tts.assert_not_called()
    worker.add_to_queue.assert_called_once()


def test_streamed_text_skips_local_load_when_gui_has_daemon_capability():
    daemon_client = object()
    worker = SimpleNamespace(
        application_settings=SimpleNamespace(tts_enabled=True),
        tts_enabled=True,
        logger=SimpleNamespace(debug=lambda *args, **kwargs: None),
        refresh_api_reference=Mock(
            return_value=SimpleNamespace(
                daemon_client=daemon_client,
                headless=False,
            )
        ),
        _failed_model=None,
        chatbot_voice_settings=SimpleNamespace(model_type="OpenVoice"),
        tts=None,
        do_interrupt=False,
        add_to_queue=Mock(),
        _load_tts=Mock(),
        _daemon_client=lambda: None,
        _active_tts_model=lambda: "OpenVoice",
    )
    worker._current_api = lambda: TTSGeneratorWorker._current_api(worker)
    worker._has_daemon_tts_capability = lambda: (
        TTSGeneratorWorker._has_daemon_tts_capability(worker)
    )

    TTSGeneratorWorker.on_llm_text_streamed_signal(
        worker,
        {
            "response": SimpleNamespace(
                action=LLMActionType.CHAT,
                is_system_message=False,
                is_end_of_message=False,
                message="hello",
            )
        },
    )

    worker._load_tts.assert_not_called()
    worker.add_to_queue.assert_called_once()


def test_streamed_text_does_not_reload_local_tts_while_loading():
    worker = SimpleNamespace(
        application_settings=SimpleNamespace(tts_enabled=True),
        tts_enabled=True,
        logger=SimpleNamespace(debug=lambda *args, **kwargs: None),
        refresh_api_reference=Mock(return_value=SimpleNamespace(headless=False)),
        _failed_model=None,
        chatbot_voice_settings=SimpleNamespace(model_type="OpenVoice"),
        tts=SimpleNamespace(model_status={ModelType.TTS: ModelStatus.LOADING}),
        do_interrupt=False,
        add_to_queue=Mock(),
        _load_tts=Mock(),
        _daemon_client=lambda: None,
        _active_tts_model=lambda: "OpenVoice",
    )
    worker._current_tts_status = lambda: TTSGeneratorWorker._current_tts_status(
        worker
    )

    TTSGeneratorWorker.on_llm_text_streamed_signal(
        worker,
        {
            "response": SimpleNamespace(
                action=LLMActionType.CHAT,
                is_system_message=False,
                is_end_of_message=False,
                message="hello",
            )
        },
    )

    worker._load_tts.assert_not_called()
    worker.add_to_queue.assert_called_once()


def test_streamed_text_queues_empty_end_of_message_for_flush():
    worker = SimpleNamespace(
        application_settings=SimpleNamespace(tts_enabled=True),
        tts_enabled=True,
        logger=SimpleNamespace(debug=lambda *args, **kwargs: None),
        refresh_api_reference=Mock(return_value=SimpleNamespace(headless=False)),
        _failed_model=None,
        chatbot_voice_settings=SimpleNamespace(model_type="OpenVoice"),
        tts=SimpleNamespace(model_status={ModelType.TTS: ModelStatus.LOADED}),
        do_interrupt=False,
        add_to_queue=Mock(),
        _load_tts=Mock(),
        _daemon_client=lambda: None,
        _active_tts_model=lambda: "OpenVoice",
    )
    worker._current_tts_status = lambda: TTSGeneratorWorker._current_tts_status(
        worker
    )

    TTSGeneratorWorker.on_llm_text_streamed_signal(
        worker,
        {
            "response": SimpleNamespace(
                action=LLMActionType.CHAT,
                is_system_message=False,
                is_end_of_message=True,
                message="",
            )
        },
    )

    worker._load_tts.assert_not_called()
    worker.add_to_queue.assert_called_once_with(
        {"message": "", "is_end_of_message": True}
    )


def test_streamed_text_ignores_visible_chunks_while_thinking():
    worker = SimpleNamespace(
        application_settings=SimpleNamespace(tts_enabled=True),
        tts_enabled=True,
        logger=SimpleNamespace(debug=lambda *args, **kwargs: None),
        refresh_api_reference=Mock(return_value=SimpleNamespace(headless=False)),
        _failed_model=None,
        chatbot_voice_settings=SimpleNamespace(model_type="OpenVoice"),
        tts=SimpleNamespace(model_status={ModelType.TTS: ModelStatus.LOADED}),
        do_interrupt=False,
        add_to_queue=Mock(),
        _load_tts=Mock(),
        _daemon_client=lambda: None,
        _active_tts_model=lambda: "OpenVoice",
    )
    worker._current_tts_status = lambda: TTSGeneratorWorker._current_tts_status(
        worker
    )

    TTSGeneratorWorker.on_llm_thinking_signal(
        worker,
        {"status": "started", "content": "", "request_id": "req-1"},
    )
    TTSGeneratorWorker.on_llm_text_streamed_signal(
        worker,
        {
            "response": SimpleNamespace(
                action=LLMActionType.CHAT,
                is_system_message=False,
                is_end_of_message=False,
                is_first_message=True,
                request_id="req-1",
                message='Okay,the user said" Hello".I need to respond.',
            )
        },
    )

    worker.add_to_queue.assert_not_called()


def test_streamed_text_strips_compact_thinking_prefix_for_tts():
    worker = SimpleNamespace(
        application_settings=SimpleNamespace(tts_enabled=True),
        tts_enabled=True,
        logger=SimpleNamespace(debug=lambda *args, **kwargs: None),
        refresh_api_reference=Mock(return_value=SimpleNamespace(headless=False)),
        _failed_model=None,
        chatbot_voice_settings=SimpleNamespace(model_type="OpenVoice"),
        tts=SimpleNamespace(model_status={ModelType.TTS: ModelStatus.LOADED}),
        do_interrupt=False,
        add_to_queue=Mock(),
        _load_tts=Mock(),
        _daemon_client=lambda: None,
        _active_tts_model=lambda: "OpenVoice",
    )
    worker._current_tts_status = lambda: TTSGeneratorWorker._current_tts_status(
        worker
    )

    TTSGeneratorWorker.on_llm_thinking_signal(
        worker,
        {
            "status": "completed",
            "content": 'Okay, the user said "Hello". I need to respond.',
            "request_id": "req-1",
        },
    )
    TTSGeneratorWorker.on_llm_text_streamed_signal(
        worker,
        {
            "response": SimpleNamespace(
                action=LLMActionType.CHAT,
                is_system_message=False,
                is_end_of_message=False,
                is_first_message=True,
                request_id="req-1",
                message='Okay,the user said" Hello".I need to respond.Hello!',
            )
        },
    )

    worker.add_to_queue.assert_called_once_with(
        {"message": "Hello!", "is_end_of_message": False}
    )


def test_handle_message_flushes_buffer_on_empty_end_of_message():
    worker = SimpleNamespace(
        do_interrupt=False,
        tokens=["Hello there"],
        _sentence_buffer=[],
        _generate=Mock(),
        play_queue_started=False,
    )

    TTSGeneratorWorker.handle_message(
        worker,
        {"message": "", "is_end_of_message": True},
    )

    worker._generate.assert_called_once_with("Hello there")
    assert worker.play_queue_started is True
    assert worker.tokens == []


def test_handle_message_preserves_word_boundaries_between_chunks():
    worker = SimpleNamespace(
        do_interrupt=False,
        tokens=[],
        _sentence_buffer=[],
        _generate=Mock(),
        play_queue_started=False,
        SENTENCE_BUFFER_SIZE=2,
        MIN_WORDS_FOR_GENERATION=8,
    )

    TTSGeneratorWorker.handle_message(
        worker,
        {"message": "Hello", "is_end_of_message": False},
    )
    TTSGeneratorWorker.handle_message(
        worker,
        {"message": "world!", "is_end_of_message": False},
    )
    TTSGeneratorWorker.handle_message(
        worker,
        {"message": "", "is_end_of_message": True},
    )

    worker._generate.assert_called_once_with("Hello world!")
    assert worker.tokens == []


def test_handle_message_generates_earlier_for_daemon_backed_tts():
    worker = SimpleNamespace(
        do_interrupt=False,
        tokens=[],
        _sentence_buffer=[],
        _generate=Mock(),
        play_queue_started=False,
        SENTENCE_BUFFER_SIZE=2,
        MIN_WORDS_FOR_GENERATION=8,
        DAEMON_MIN_WORDS_FOR_GENERATION=4,
        _daemon_client=lambda: object(),
    )

    TTSGeneratorWorker.handle_message(
        worker,
        {
            "message": "Hello! How are you today? I'm here",
            "is_end_of_message": False,
        },
    )

    worker._generate.assert_called_once_with("Hello! How are you today?")
    assert worker.play_queue_started is True
    assert worker.tokens == ["I'm here"]


def test_load_tts_marks_model_failed_when_load_returns_false():
    worker = SimpleNamespace(
        tts_enabled=True,
        logger=SimpleNamespace(info=lambda *args, **kwargs: None),
        tts=SimpleNamespace(load=Mock(return_value=False)),
        _failed_model=None,
        _daemon_client=lambda: None,
        _active_tts_model=lambda: "OpenVoice",
        _initialize_tts_model_manager=Mock(),
        _report_tts_load_error=Mock(),
    )

    TTSGeneratorWorker._load_tts(worker)

    assert worker._failed_model == "OpenVoice"
    assert worker.tts is None
    worker._report_tts_load_error.assert_not_called()


def test_load_tts_marks_model_failed_on_unexpected_error():
    error = ValueError("signal only works in main thread")
    worker = SimpleNamespace(
        tts_enabled=True,
        logger=SimpleNamespace(info=lambda *args, **kwargs: None),
        tts=SimpleNamespace(load=Mock(side_effect=error)),
        _failed_model=None,
        _daemon_client=lambda: None,
        _active_tts_model=lambda: "OpenVoice",
        _initialize_tts_model_manager=Mock(),
        _report_tts_load_error=Mock(),
    )

    TTSGeneratorWorker._load_tts(worker)

    assert worker._failed_model == "OpenVoice"
    assert worker.tts is None
    worker._report_tts_load_error.assert_called_once_with(error)


def test_generate_emits_local_openvoice_audio_to_vocalizer_signal():
    audio = [0.1, 0.2, 0.3]
    worker = SimpleNamespace(
        do_interrupt=False,
        logger=SimpleNamespace(debug=lambda *args, **kwargs: None),
        chatbot_voice_settings=SimpleNamespace(model_type="OpenVoice"),
        chatbot=SimpleNamespace(gender="male"),
        tts=SimpleNamespace(generate=Mock(return_value=audio)),
        emit_signal=Mock(),
        _daemon_client=lambda: None,
    )

    TTSGeneratorWorker._generate(worker, "Hello there.")

    worker.tts.generate.assert_called_once()
    worker.emit_signal.assert_called_once_with(
        SignalCode.TTS_GENERATOR_WORKER_ADD_TO_STREAM_SIGNAL,
        {"message": audio},
    )


def test_generate_falls_back_to_local_tts_after_daemon_error():
    audio = [0.1, 0.2, 0.3]
    worker = SimpleNamespace(
        do_interrupt=False,
        logger=SimpleNamespace(
            debug=lambda *args, **kwargs: None,
            warning=lambda *args, **kwargs: None,
        ),
        chatbot_voice_settings=SimpleNamespace(model_type="OpenVoice"),
        chatbot=SimpleNamespace(gender="male"),
        tts=SimpleNamespace(generate=Mock(return_value=audio)),
        emit_signal=Mock(),
        _daemon_client=lambda: object(),
        _generate_via_daemon=Mock(return_value=None),
    )

    TTSGeneratorWorker._generate(worker, "Hello there.")

    worker._generate_via_daemon.assert_called_once_with(
        "Hello there.",
        "OpenVoice",
    )
    worker.tts.generate.assert_called_once()
    worker.emit_signal.assert_called_once_with(
        SignalCode.TTS_GENERATOR_WORKER_ADD_TO_STREAM_SIGNAL,
        {"message": audio},
    )


def test_generate_loads_local_tts_before_fallback_generation():
    audio = [0.1, 0.2, 0.3]
    tts = SimpleNamespace(generate=Mock(return_value=audio))
    worker = SimpleNamespace(
        do_interrupt=False,
        logger=SimpleNamespace(debug=lambda *args, **kwargs: None),
        chatbot_voice_settings=SimpleNamespace(model_type="OpenVoice"),
        chatbot=SimpleNamespace(gender="male"),
        tts=None,
        emit_signal=Mock(),
        _daemon_client=lambda: None,
        _load_tts=Mock(),
        _current_tts_status=lambda: ModelStatus.UNLOADED,
        _failed_model=None,
    )

    def load_tts():
        worker.tts = tts

    worker._load_tts.side_effect = load_tts

    TTSGeneratorWorker._generate(worker, "Hello there.")

    worker._load_tts.assert_called_once_with()
    tts.generate.assert_called_once()
    worker.emit_signal.assert_called_once_with(
        SignalCode.TTS_GENERATOR_WORKER_ADD_TO_STREAM_SIGNAL,
        {"message": audio},
    )


def test_english_falls_back_when_nltk_tagger_data_is_missing():
    from airunner.vendor.melo.text.english import English

    class FakeG2P:
        cmu = {}
        homograph2features = {}

        def __call__(self, _word):
            raise LookupError("missing averaged_perceptron_tagger_eng")

        @staticmethod
        def predict(_word):
            return ["HH", "AH0", "L", "OW1"]

    english = English.__new__(English)
    english.logger = SimpleNamespace(warning=lambda *args, **kwargs: None)
    english._warned_missing_nltk_tagger = False
    english.eng_dict = {}
    english._g2p = FakeG2P()
    english.arpa = {"HH", "AH0", "L", "OW1"}

    phones, tones, word2ph = English.call(
        english,
        "hello",
        pad_start_end=False,
        tokenized=["hello"],
    )

    assert phones == ["hh", "ah", "l", "ow"]
    assert tones == [0, 1, 0, 2]
    assert word2ph == [1, 1, 1, 1]