from airunner.components.llm.api.llm_services import LLMAPIService
from airunner.components.llm.managers.llm_request import LLMRequest


def test_send_request_accepts_system_prompt():
    """Ensure LLMAPIService.send_request accepts 'system_prompt' extra kw and applies it to llm_request."""
    service = LLMAPIService()
    req = LLMRequest()
    # Should not raise an exception
    service.send_request(
        prompt="Hello",
        llm_request=req,
        action=None,
        system_prompt="You are a helpful assistant",
    )
    # Ensure property was set on the llm_request
    assert getattr(req, "system_prompt", None) == "You are a helpful assistant"


def test_send_request_includes_conversation_id():
    """Verify that conversation_id is forwarded with the emitted signal."""
    service = LLMAPIService()
    emitted = {}

    def _capture(signal, payload):
        emitted["signal"] = signal
        emitted["payload"] = payload

    service.emit_signal = _capture

    service.send_request(prompt="Hi", conversation_id=987)

    assert emitted["payload"].get("conversation_id") == 987
