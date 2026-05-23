"""Tests for local fallback runtime clients."""

import base64
import io
from queue import Queue
from types import SimpleNamespace
from unittest.mock import Mock

import numpy as np
from PIL import Image

from airunner_services.art.managers.stablediffusion.image_response import (
    ImageResponse,
)
from airunner_services.contract_enums import ModelStatus, ModelType, SignalCode
from airunner_services.ipc.messages import EnvelopeStatus, RequestEnvelope
from airunner.runtimes.contracts import (
    ChatMessage,
    MessageRole,
    RuntimeAction,
    RuntimeHealthStatus,
    RuntimeKind,
)
from airunner_services.runtimes.local_fallback import (
    LocalFallbackArtClient,
    LocalFallbackLLMClient,
    LocalFallbackSTTClient,
    LocalFallbackTTSClient,
    register_local_fallback_clients,
)
from airunner.runtimes.registry import RuntimeRegistry


class FakeMediator:
    """Minimal mediator for pending-request and signal tests."""

    def __init__(self):
        self.queues = {}
        self.handlers = {}
        self.unregistered = []

    def seed(self, request_id: str, *responses: object) -> None:
        queue = Queue()
        for response in responses:
            queue.put({"response": response})
        self.queues[request_id] = queue

    def register_pending_request(self, request_id: str) -> Queue:
        return self.queues.setdefault(request_id, Queue())

    def unregister_pending_request(self, request_id: str) -> None:
        self.unregistered.append(request_id)

    def register(self, code, slot_function) -> None:
        self.handlers.setdefault(code, []).append(slot_function)

    def unregister(self, code, slot_function) -> None:
        callbacks = self.handlers.get(code, [])
        self.handlers[code] = [
            callback
            for callback in callbacks
            if callback is not slot_function
        ]

    def emit_signal(self, code, data=None) -> None:
        for callback in list(self.handlers.get(code, [])):
            callback(data or {})


class FakeLLMService:
    """Minimal LLM service double used by fallback client tests."""

    def __init__(self):
        self.requests = []
        self.interrupted = False

    def send_request(self, **kwargs) -> None:
        self.requests.append(kwargs)

    def interrupt(self) -> None:
        self.interrupted = True


class FakeSignalSource:
    """Signal emitter with deterministic responses for adapter tests."""

    def __init__(self, mediator: FakeMediator, responders=None):
        self.mediator = mediator
        self.responders = responders or {}
        self.emitted = []

    def emit_signal(self, code, data=None) -> None:
        payload = data or {}
        self.emitted.append((code, payload))
        responder = self.responders.get(code)
        if responder is not None:
            responder(payload)

    def play_audio(self, message: str) -> None:
        self.emitted.append(("play_audio", {"message": message}))


def _llm_request(request_id: str = "req-1") -> RequestEnvelope:
    return RequestEnvelope(
        request_id=request_id,
        runtime=RuntimeKind.LLM,
        action=RuntimeAction.INVOKE,
        payload={
            "messages": [
                ChatMessage(
                    role=MessageRole.SYSTEM,
                    content="You are concise.",
                ).model_dump(),
                ChatMessage(
                    role=MessageRole.USER,
                    content="Say hi",
                ).model_dump(),
            ],
            "temperature": 0.2,
            "max_tokens": 32,
            "tool_choice": "calendar_tool",
        },
    )


class TestLocalFallbackLLMClient:
    """Tests for the LLM local fallback client."""

    def test_invoke_aggregates_streamed_chunks(self):
        mediator = FakeMediator()
        mediator.seed(
            "req-1",
            SimpleNamespace(message="Hello", is_end_of_message=False),
            SimpleNamespace(
                message=" world",
                is_end_of_message=True,
                total_tokens=7,
            ),
        )
        service = FakeLLMService()
        client = LocalFallbackLLMClient(
            mediator=mediator,
            llm_service=service,
            llm_request_factory=lambda _invocation: SimpleNamespace(),
        )

        response = client.invoke(_llm_request())

        assert response.status == EnvelopeStatus.SUCCEEDED
        assert response.payload["content"] == "Hello world"
        assert response.metadata["total_tokens"] == 7
        assert service.requests[0]["prompt"] == "Say hi"
        assert service.requests[0]["request_id"] == "req-1"
        assert (
            service.requests[0]["llm_request"].system_prompt
            == "You are concise."
        )
        assert service.requests[0]["llm_request"].force_tool == "calendar_tool"
        assert mediator.unregistered == ["req-1"]

    def test_stream_yields_response_deltas(self):
        mediator = FakeMediator()
        mediator.seed(
            "req-1",
            SimpleNamespace(message="Hel", is_end_of_message=False),
            SimpleNamespace(message="lo", is_end_of_message=True),
        )
        client = LocalFallbackLLMClient(
            mediator=mediator,
            llm_service=FakeLLMService(),
            llm_request_factory=lambda _invocation: SimpleNamespace(),
        )

        deltas = list(client.stream(_llm_request()))

        assert [delta.delta["content"] for delta in deltas] == ["Hel", "lo"]
        assert deltas[-1].final is True
        assert mediator.unregistered == ["req-1"]

    def test_cancel_interrupts_legacy_service(self):
        service = FakeLLMService()
        client = LocalFallbackLLMClient(
            mediator=FakeMediator(),
            llm_service=service,
            llm_request_factory=lambda _invocation: SimpleNamespace(),
        )

        response = client.cancel("req-9")

        assert service.interrupted is True
        assert response.status == EnvelopeStatus.CANCELLED
        assert response.metadata["best_effort"] is True


class TestLocalFallbackSTTClient:
    """Tests for the STT local fallback client."""

    def test_invoke_returns_transcription(self):
        mediator = FakeMediator()
        signal_source = FakeSignalSource(
            mediator,
            responders={
                SignalCode.AUDIO_CAPTURE_WORKER_RESPONSE_SIGNAL: (
                    lambda _payload: mediator.emit_signal(
                        SignalCode.AUDIO_PROCESSOR_RESPONSE_SIGNAL,
                        {
                            "transcription": {
                                "text": "hello world",
                                "language": "en",
                            }
                        },
                    )
                )
            },
        )
        client = LocalFallbackSTTClient(
            mediator=mediator,
            signal_source=signal_source,
        )

        response = client.invoke(
            RequestEnvelope(
                request_id="req-stt",
                runtime=RuntimeKind.STT,
                action=RuntimeAction.INVOKE,
                payload={
                    "audio_b64": base64.b64encode(b"audio").decode("ascii"),
                },
            )
        )

        assert response.status == EnvelopeStatus.SUCCEEDED
        assert response.payload == {"text": "hello world", "language": "en"}

    def test_timeout_returns_failure(self):
        mediator = FakeMediator()
        client = LocalFallbackSTTClient(
            mediator=mediator,
            signal_source=FakeSignalSource(mediator),
            timeout_seconds=0.01,
        )

        response = client.invoke(
            RequestEnvelope(
                request_id="req-timeout",
                runtime=RuntimeKind.STT,
                action=RuntimeAction.INVOKE,
                payload={
                    "audio_b64": base64.b64encode(b"audio").decode("ascii"),
                },
            )
        )

        assert response.status == EnvelopeStatus.FAILED
        assert response.error.code == "stt_timeout"

    def test_load_updates_health_and_cancel_interrupts(self):
        mediator = FakeMediator()
        signal_source = FakeSignalSource(
            mediator,
            responders={
                SignalCode.STT_LOAD_SIGNAL: (
                    lambda _payload: mediator.emit_signal(
                        SignalCode.MODEL_STATUS_CHANGED_SIGNAL,
                        {
                            "model": ModelType.STT,
                            "status": ModelStatus.LOADED,
                        },
                    )
                )
            },
        )
        client = LocalFallbackSTTClient(
            mediator=mediator,
            signal_source=signal_source,
        )

        load_response = client.invoke(
            RequestEnvelope(
                request_id="req-load",
                runtime=RuntimeKind.STT,
                action=RuntimeAction.LOAD_MODEL,
            )
        )
        cancel_response = client.cancel("req-cancel")

        assert load_response.status == EnvelopeStatus.SUCCEEDED
        assert client.healthcheck().status == RuntimeHealthStatus.READY
        assert cancel_response.status == EnvelopeStatus.CANCELLED
        assert signal_source.emitted[-1][0] == SignalCode.INTERRUPT_PROCESS_SIGNAL


class TestLocalFallbackTTSClient:
    """Tests for the TTS local fallback client."""

    def test_invoke_and_model_control_paths(self):
        mediator = FakeMediator()
        signal_source = FakeSignalSource(
            mediator,
            responders={
                SignalCode.TTS_ENABLE_SIGNAL: (
                    lambda _payload: mediator.emit_signal(
                        SignalCode.MODEL_STATUS_CHANGED_SIGNAL,
                        {
                            "model": ModelType.TTS,
                            "status": ModelStatus.LOADED,
                        },
                    )
                ),
                SignalCode.TTS_DISABLE_SIGNAL: (
                    lambda _payload: mediator.emit_signal(
                        SignalCode.MODEL_STATUS_CHANGED_SIGNAL,
                        {
                            "model": ModelType.TTS,
                            "status": ModelStatus.UNLOADED,
                        },
                    )
                ),
            },
        )
        client = LocalFallbackTTSClient(
            mediator=mediator,
            signal_source=signal_source,
        )

        invoke_response = client.invoke(
            RequestEnvelope(
                request_id="req-tts",
                runtime=RuntimeKind.TTS,
                action=RuntimeAction.INVOKE,
                payload={"text": "hello there"},
            )
        )
        load_response = client.invoke(
            RequestEnvelope(
                request_id="req-tts-load",
                runtime=RuntimeKind.TTS,
                action=RuntimeAction.LOAD_MODEL,
            )
        )
        unload_response = client.invoke(
            RequestEnvelope(
                request_id="req-tts-unload",
                runtime=RuntimeKind.TTS,
                action=RuntimeAction.UNLOAD_MODEL,
            )
        )
        cancel_response = client.cancel("req-tts-cancel")

        assert invoke_response.payload["accepted"] is True
        assert signal_source.emitted[0] == (
            "play_audio",
            {"message": "hello there"},
        )
        assert load_response.status == EnvelopeStatus.SUCCEEDED
        assert unload_response.status == EnvelopeStatus.SUCCEEDED
        assert client.healthcheck().status == RuntimeHealthStatus.STOPPED
        assert cancel_response.status == EnvelopeStatus.CANCELLED

    def test_invoke_returns_audio_payload_in_headless_mode(self):
        manager = SimpleNamespace(
            generate=lambda _request: np.array([0.0, 0.1], dtype=np.float32),
            load=lambda: True,
            tone_color_converter=SimpleNamespace(
                hps=SimpleNamespace(
                    data=SimpleNamespace(sampling_rate=24000)
                )
            ),
        )
        worker = SimpleNamespace(
            tts=manager,
            chatbot=SimpleNamespace(gender="Female"),
            _current_tts_status=lambda: ModelStatus.LOADED,
            _active_tts_model=lambda: "OpenVoice",
        )
        signal_source = SimpleNamespace(
            _worker_manager=SimpleNamespace(tts_generator_worker=worker)
        )
        client = LocalFallbackTTSClient(signal_source=signal_source)

        response = client.invoke(
            RequestEnvelope(
                request_id="req-tts-audio",
                runtime=RuntimeKind.TTS,
                action=RuntimeAction.INVOKE,
                payload={"text": "hello there"},
            )
        )

        assert response.status is EnvelopeStatus.SUCCEEDED
        assert response.payload["accepted"] is True
        assert base64.b64decode(response.payload["audio_b64"])[0:4] == b"RIFF"

    def test_invoke_does_not_queue_playback_when_headless_audio_fails(self):
        signal_source = FakeSignalSource(FakeMediator())
        signal_source._worker_manager = SimpleNamespace(
            tts_generator_worker=SimpleNamespace(
                tts=SimpleNamespace(load=lambda: False),
                _current_tts_status=lambda: None,
                _active_tts_model=lambda: "OpenVoice",
            )
        )
        client = LocalFallbackTTSClient(signal_source=signal_source)

        response = client.invoke(
            RequestEnvelope(
                request_id="req-tts-audio-fail",
                runtime=RuntimeKind.TTS,
                action=RuntimeAction.INVOKE,
                payload={"text": "hello there"},
            )
        )

        assert response.status is EnvelopeStatus.FAILED
        assert signal_source.emitted == []


class TestLocalFallbackArtClient:
    """Tests for the art local fallback client."""

    def test_invoke_returns_encoded_images(self):
        mediator = FakeMediator()
        observed_request = {}

        def respond_to_generate(payload):
            observed_request["model_path"] = payload["image_request"].model_path
            observed_request["pipeline_action"] = (
                payload["image_request"].pipeline_action
            )
            observed_request["version"] = payload["image_request"].version
            observed_request["scheduler"] = (
                payload["image_request"].scheduler
            )
            observed_request["skip_auto_export"] = (
                payload["image_request"].skip_auto_export
            )
            payload["image_request"].callback(
                ImageResponse(
                    images=[Image.new("RGB", (1, 1), "white")],
                    data={"seed": 1},
                    active_rect=None,
                    is_outpaint=False,
                )
            )

        signal_source = FakeSignalSource(
            mediator,
            responders={SignalCode.DO_GENERATE_SIGNAL: respond_to_generate},
        )
        client = LocalFallbackArtClient(
            mediator=mediator,
            signal_source=signal_source,
        )

        response = client.invoke(
            RequestEnvelope(
                request_id="req-art",
                runtime=RuntimeKind.ART,
                action=RuntimeAction.INVOKE,
                payload={
                    "prompt": "mountains",
                    "model": "/models/zimage.safetensors",
                    "metadata": {
                        "version": "Z-Image Turbo",
                        "scheduler": "Flow Match Euler",
                        "skip_auto_export": True,
                    },
                },
            )
        )
        cancel_response = client.cancel("req-art-cancel")
        unload_response = client.invoke(
            RequestEnvelope(
                request_id="req-art-unload",
                runtime=RuntimeKind.ART,
                action=RuntimeAction.UNLOAD_MODEL,
            )
        )

        assert response.status == EnvelopeStatus.SUCCEEDED
        assert response.payload["image_count"] == 1
        assert response.payload["images"][0]
        assert observed_request == {
            "model_path": "/models/zimage.safetensors",
            "pipeline_action": "txt2img",
            "version": "Z-Image Turbo",
            "scheduler": "Flow Match Euler",
            "skip_auto_export": True,
        }
        assert all(
            code != SignalCode.SD_ART_MODEL_CHANGED
            for code, _payload in signal_source.emitted
        )
        assert cancel_response.status == EnvelopeStatus.CANCELLED
        assert unload_response.payload["accepted"] is True

    def test_invoke_with_progress_reports_signal_updates(self):
        mediator = FakeMediator()
        progress_updates = []

        def respond_to_generate(payload):
            mediator.emit_signal(
                SignalCode.SD_PROGRESS_SIGNAL,
                {"step": 2, "total": 4},
            )
            payload["image_request"].callback(
                ImageResponse(
                    images=[Image.new("RGB", (1, 1), "white")],
                    data={"seed": 1},
                    active_rect=None,
                    is_outpaint=False,
                )
            )

        signal_source = FakeSignalSource(
            mediator,
            responders={SignalCode.DO_GENERATE_SIGNAL: respond_to_generate},
        )
        client = LocalFallbackArtClient(
            mediator=mediator,
            signal_source=signal_source,
        )

        response = client.invoke_with_progress(
            RequestEnvelope(
                request_id="req-art-progress",
                runtime=RuntimeKind.ART,
                action=RuntimeAction.INVOKE,
                payload={"prompt": "mountains"},
            ),
            progress_updates.append,
        )

        assert response.status == EnvelopeStatus.SUCCEEDED
        assert progress_updates == [
            {
                "status": "running",
                "progress": 1.0,
                "phase": "dispatch",
            },
            {
                "status": "running",
                "progress": 50.0,
                "step": 2,
                "total": 4,
            }
        ]

    def test_invoke_can_decode_img2img_request_metadata(self):
        mediator = FakeMediator()
        observed_request = {}
        image_buffer = io.BytesIO()
        Image.new("RGB", (2, 2), "white").save(image_buffer, format="PNG")
        image_b64 = base64.b64encode(image_buffer.getvalue()).decode("ascii")

        def respond_to_generate(payload):
            request = payload["image_request"]
            observed_request["pipeline_action"] = request.pipeline_action
            observed_request["generator_section"] = (
                request.generator_section.value
            )
            observed_request["strength"] = request.strength
            observed_request["image_size"] = request.image.size
            request.callback(
                ImageResponse(
                    images=[Image.new("RGB", (1, 1), "white")],
                    data={"seed": 1},
                    active_rect=None,
                    is_outpaint=False,
                )
            )

        signal_source = FakeSignalSource(
            mediator,
            responders={SignalCode.DO_GENERATE_SIGNAL: respond_to_generate},
        )
        client = LocalFallbackArtClient(
            mediator=mediator,
            signal_source=signal_source,
        )

        response = client.invoke(
            RequestEnvelope(
                request_id="req-art-img2img",
                runtime=RuntimeKind.ART,
                action=RuntimeAction.INVOKE,
                payload={
                    "prompt": "mountains",
                    "metadata": {
                        "pipeline": "img2img",
                        "strength": 0.35,
                        "image_b64": image_b64,
                    },
                },
            )
        )

        assert response.status == EnvelopeStatus.SUCCEEDED
        assert observed_request == {
            "pipeline_action": "img2img",
            "generator_section": "img2img",
            "strength": 0.35,
            "image_size": (2, 2),
        }

    def test_healthcheck_includes_active_art_model_metadata(self):
        """Art health summaries should retain the active model identity."""
        mediator = FakeMediator()

        def respond_to_generate(payload):
            payload["image_request"].callback(
                ImageResponse(
                    images=[Image.new("RGB", (1, 1), "white")],
                    data={"seed": 1},
                    active_rect=None,
                    is_outpaint=False,
                )
            )

        signal_source = FakeSignalSource(
            mediator,
            responders={SignalCode.DO_GENERATE_SIGNAL: respond_to_generate},
        )
        client = LocalFallbackArtClient(
            mediator=mediator,
            signal_source=signal_source,
        )

        client.invoke(
            RequestEnvelope(
                request_id="req-art-health",
                runtime=RuntimeKind.ART,
                action=RuntimeAction.INVOKE,
                payload={
                    "prompt": "mountains",
                    "model": "/models/zimage.safetensors",
                    "metadata": {"version": "Z-Image Turbo"},
                },
            )
        )

        health = client.healthcheck()

        assert health.metadata["model_path"] == "/models/zimage.safetensors"
        assert health.metadata["model_version"] == "Z-Image Turbo"

    def test_invoke_can_remove_background_through_rmbg_manager(
        self,
        monkeypatch,
    ):
        mediator = FakeMediator()
        signal_source = FakeSignalSource(mediator)
        client = LocalFallbackArtClient(
            mediator=mediator,
            signal_source=signal_source,
        )

        manager = SimpleNamespace(
            remove_background_to_png_bytes=lambda _image: b"png-bytes"
        )
        monkeypatch.setattr(client, "_rmbg_manager", lambda: manager)

        image_buffer = io.BytesIO()
        Image.new("RGB", (2, 2), "white").save(image_buffer, format="PNG")
        image_b64 = base64.b64encode(image_buffer.getvalue()).decode("ascii")

        response = client.invoke(
            RequestEnvelope(
                request_id="req-art-rmbg",
                runtime=RuntimeKind.ART,
                action=RuntimeAction.INVOKE,
                payload={
                    "prompt": "",
                    "metadata": {"image_b64": image_b64},
                },
                metadata={"operation": "remove_background"},
            )
        )

        assert response.status == EnvelopeStatus.SUCCEEDED
        assert response.payload["image_count"] == 1
        assert response.payload["images"][0]

    def test_load_and_unload_art_components(self):
        mediator = FakeMediator()
        signal_source = FakeSignalSource(mediator)
        manager = SimpleNamespace(
            _load_safety_checker=lambda: True,
            _unload_safety_checker=Mock(),
        )
        signal_source._worker_manager = SimpleNamespace(
            sd_worker=SimpleNamespace(model_manager=manager),
            _sd_worker=SimpleNamespace(model_manager=manager),
        )
        client = LocalFallbackArtClient(
            mediator=mediator,
            signal_source=signal_source,
        )
        client._rmbg_model_manager = SimpleNamespace(
            _load=Mock(),
            unload=Mock(),
        )

        rmbg_load = client.invoke(
            RequestEnvelope(
                request_id="req-art-rmbg-load",
                runtime=RuntimeKind.ART,
                action=RuntimeAction.LOAD_MODEL,
                metadata={"component": "rmbg"},
            )
        )
        safety_unload = client.invoke(
            RequestEnvelope(
                request_id="req-art-safety-unload",
                runtime=RuntimeKind.ART,
                action=RuntimeAction.UNLOAD_MODEL,
                metadata={"component": "safety_checker"},
            )
        )

        assert rmbg_load.status == EnvelopeStatus.SUCCEEDED
        assert safety_unload.status == EnvelopeStatus.SUCCEEDED
        client._rmbg_model_manager._load.assert_called_once_with()
        manager._unload_safety_checker.assert_called_once_with()


class TestLocalFallbackRegistry:
    """Tests for local fallback registry registration."""

    def test_registers_all_local_fallback_routes(self):
        mediator = FakeMediator()
        signal_source = FakeSignalSource(mediator)
        registry = RuntimeRegistry()

        register_local_fallback_clients(
            registry,
            llm_client=LocalFallbackLLMClient(
                mediator=mediator,
                llm_service=FakeLLMService(),
                llm_request_factory=lambda _invocation: SimpleNamespace(),
            ),
            stt_client=LocalFallbackSTTClient(
                mediator=mediator,
                signal_source=signal_source,
            ),
            tts_client=LocalFallbackTTSClient(
                mediator=mediator,
                signal_source=signal_source,
            ),
            art_client=LocalFallbackArtClient(
                mediator=mediator,
                signal_source=signal_source,
            ),
        )

        for runtime in (
            RuntimeKind.LLM,
            RuntimeKind.STT,
            RuntimeKind.TTS,
            RuntimeKind.ART,
        ):
            assert registry.resolve(runtime, provider="local")
            assert registry.resolve(
                runtime,
                provider="local",
                deployment_mode="local_fallback",
            )