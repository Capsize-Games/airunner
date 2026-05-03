"""Focused tests for FastAPI legacy compatibility routes."""

from types import SimpleNamespace

from airunner.api.routes import legacy


def test_legacy_admin_shutdown_schedules_process_exit(monkeypatch):
    scheduled = []

    monkeypatch.setattr(
        legacy,
        "_schedule_process_shutdown",
        lambda delay_seconds=0.1: scheduled.append(delay_seconds),
    )

    response = legacy.legacy_admin_shutdown()

    assert response == {"status": "ok", "shutting_down": True}
    assert scheduled == [0.1]


def test_legacy_llm_generate_disables_tts_for_stream_bridge(monkeypatch):
    captured = {}

    class ImmediateThread:
        def __init__(self, *, target=None, args=(), daemon=None):
            self._target = target
            self._args = args

        def start(self):
            if self._target is not None:
                self._target(*self._args)

    def send_request(**kwargs):
        captured.update(kwargs)

    api = SimpleNamespace(llm=SimpleNamespace(send_request=send_request))

    monkeypatch.setattr(legacy, "_get_airunner_api", lambda _req: api)
    monkeypatch.setattr(legacy.threading, "Thread", ImmediateThread)

    body = legacy.LegacyLLMGenerateRequest(prompt="Hello", stream=True)
    request = SimpleNamespace(headers={})

    legacy.legacy_llm_generate(body, request)

    assert captured["prompt"] == "Hello"
    assert captured["do_tts_reply"] is False