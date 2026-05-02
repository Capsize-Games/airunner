"""Tests for runtime contracts and descriptors."""

from airunner.runtimes.contracts import (
    ArtInvocationResponse,
    ArtInvocationRequest,
    ChatMessage,
    LLMInvocationRequest,
    LLMInvocationResponse,
    MessageRole,
    RuntimeDescriptor,
    RuntimeHealth,
    RuntimeHealthStatus,
    RuntimeKind,
    RuntimeMode,
    STTInvocationResponse,
    STTInvocationRequest,
    TTSInvocationResponse,
    TTSInvocationRequest,
    TransportKind,
)


def test_llm_contract_round_trip():
    request = LLMInvocationRequest(
        messages=[
            ChatMessage(role=MessageRole.USER, content="Hello"),
        ],
        temperature=0.4,
        max_tokens=32,
        metadata={"conversation_id": "abc"},
    )

    restored = LLMInvocationRequest.model_validate(request.model_dump())

    assert restored.messages[0].role == MessageRole.USER
    assert restored.max_tokens == 32
    assert restored.metadata["conversation_id"] == "abc"


def test_stt_contract_defaults():
    request = STTInvocationRequest(audio_b64="YXVkaW8=")

    assert request.mime_type == "audio/wav"
    assert request.stream is False
    assert request.metadata == {}


def test_tts_contract_defaults():
    request = TTSInvocationRequest(text="Speak")

    assert request.speed == 1.0
    assert request.stream is False
    assert request.metadata == {}


def test_art_contract_defaults():
    request = ArtInvocationRequest(prompt="mountains")

    assert request.width == 1024
    assert request.height == 1024
    assert request.num_images == 1
    assert request.metadata == {}


def test_runtime_health_round_trip():
    health = RuntimeHealth(
        descriptor=RuntimeDescriptor(
            runtime=RuntimeKind.STT,
            provider="local",
            mode=RuntimeMode.LOCAL_FALLBACK,
            transport=TransportKind.IN_PROCESS,
        ),
        status=RuntimeHealthStatus.READY,
        details="Loaded",
        metadata={"model_status": "Loaded"},
    )

    restored = RuntimeHealth.model_validate(health.model_dump())

    assert restored.descriptor.runtime == RuntimeKind.STT
    assert restored.status == RuntimeHealthStatus.READY
    assert restored.metadata["model_status"] == "Loaded"


def test_modality_response_contracts_round_trip():
    llm = LLMInvocationResponse(
        content="Hello",
        usage={"total_tokens": 4},
    )
    stt = STTInvocationResponse(text="transcript", language="en")
    tts = TTSInvocationResponse(accepted=True, audio_b64="YXVkaW8=")
    art = ArtInvocationResponse(images=["aGVsbG8="], image_count=1)

    assert LLMInvocationResponse.model_validate(llm.model_dump()).content == "Hello"
    assert STTInvocationResponse.model_validate(stt.model_dump()).language == "en"
    assert TTSInvocationResponse.model_validate(tts.model_dump()).audio_b64 == "YXVkaW8="
    assert ArtInvocationResponse.model_validate(art.model_dump()).image_count == 1