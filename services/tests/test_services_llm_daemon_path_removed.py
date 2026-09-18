"""Regression test for issue #2188's final ``llm_services.py`` finding.

Services' canonical ``airunner_services.api.services.llm_services.LLMAPIService``
was investigated (see that issue's comments) and its daemon-dispatch branch was
confirmed unreachable:

- every construction path resolves ``self.api`` to either ``None`` or a
  ``ServiceApp`` whose ``__init__`` hard-codes ``self.headless = True`` (and
  raises on ``ServiceApp(headless=False)``);
- ``_daemon_client()`` returned ``None`` whenever ``api.headless`` was true, so
  the daemon branch never ran;
- the only ``headless=False`` construction sites in the repository
  (``test_gui_llm_tts_functional.py`` / ``test_gui_stt_llm_tts_functional.py``)
  import the *desktop* class (``airunner.components.llm.api.llm_services``),
  not this one.

Per the project's dead-code convention the unreachable daemon-client mixin was
deleted outright rather than left in place. This test pins both the removal and
the surviving in-process path.
"""

from __future__ import annotations

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_SERVICES_SRC = _PROJECT_ROOT / "services" / "src"
_SERVICES_API_DIR = (
    _SERVICES_SRC / "airunner_services" / "api" / "services"
)

sys.path[:0] = [str(_SERVICES_SRC)]

# Symbols that only existed on the deleted daemon-dispatch path.
_DEAD_SYMBOLS = (
    "LLMDaemonStreamMixin",
    "_DaemonStreamState",
    "_daemon_client",
    "_stream_daemon_request",
    "_forward_daemon_chunk",
    "_response_from_daemon_chunk",
    "_build_visible_daemon_response",
    "_emit_visible_daemon_parts",
    "_extract_visible_daemon_text",
    "_start_daemon_thinking",
    "_append_daemon_thinking",
    "_finish_daemon_thinking",
    "_send_request_via_daemon",
    "_run_daemon_request_or_fallback",
    "_daemon_is_immediately_available",
    "_daemon_state_value",
    "_available_daemon_client",
    "_run_daemon_unload",
    "DaemonConnectionState",
)


def test_llm_daemon_stream_mixin_file_is_gone():
    assert not (
        _SERVICES_API_DIR / "llm_daemon_stream_mixin.py"
    ).exists()


def test_no_dead_daemon_symbols_remain_in_llm_api_services():
    offenders: dict[str, list[str]] = {}
    for path in sorted(_SERVICES_API_DIR.glob("llm*.py")):
        text = path.read_text(encoding="utf-8")
        found = [symbol for symbol in _DEAD_SYMBOLS if symbol in text]
        if found:
            offenders[path.name] = found
    assert offenders == {}


def test_no_remaining_imports_of_the_deleted_mixin():
    offenders = []
    fragment = "llm_daemon_stream_mixin"
    for path in (_SERVICES_SRC / "airunner_services").rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        if fragment in path.read_text(encoding="utf-8"):
            offenders.append(str(path))
    assert offenders == []


def test_canonical_service_no_longer_exposes_the_daemon_client():
    from airunner_services.api.services.llm_services import LLMAPIService

    assert not hasattr(LLMAPIService, "_daemon_client")
    assert not any(
        base.__name__ == "LLMDaemonStreamMixin"
        for base in LLMAPIService.__mro__
    )


def test_send_request_uses_only_the_in_process_path(monkeypatch):
    """``send_request`` must never consult a daemon client."""
    from airunner_common.contract_enums import LLMActionType
    from airunner_services.api.services.llm_services import LLMAPIService
    from airunner_services.llm.llm_request import LLMRequest
    from airunner_services.utils.application.enum_resolver import (
        signal_code_proxy,
    )

    service = LLMAPIService()
    emitted: list[tuple[object, object]] = []
    monkeypatch.setattr(
        service,
        "emit_signal",
        lambda code, data=None: emitted.append((code, data)),
    )

    consulted: list[bool] = []

    def fake_daemon_client():
        consulted.append(True)
        return object()

    monkeypatch.setattr(
        service,
        "_daemon_client",
        fake_daemon_client,
        raising=False,
    )

    service.send_request(
        "hello",
        llm_request=LLMRequest(),
        action=LLMActionType.CHAT,
    )

    assert consulted == []
    codes = [code for code, _ in emitted]
    assert signal_code_proxy().LLM_TEXT_GENERATE_REQUEST_SIGNAL in codes


def test_unload_and_interrupt_only_emit_local_signals(monkeypatch):
    from airunner_services.api.services.llm_services import LLMAPIService
    from airunner_services.utils.application.enum_resolver import (
        signal_code_proxy,
    )

    service = LLMAPIService()
    emitted: list[object] = []
    monkeypatch.setattr(
        service,
        "emit_signal",
        lambda code, data=None: emitted.append(code),
    )

    service.interrupt()
    service.unload({"reason": "test"})

    signal_code = signal_code_proxy()
    assert signal_code.INTERRUPT_PROCESS_SIGNAL in emitted
    assert signal_code.LLM_UNLOAD_SIGNAL in emitted
