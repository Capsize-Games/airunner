"""Unit tests for _send_crawler_decision.

The send/wait round-trip was extracted to keep the llm_invoke closure
within the long-function threshold. These tests pin the mediator
lifecycle: registration, request, 30-second wait, and cleanup.

The crawl tool module imports optional third-party packages (scrapy,
twisted, trafilatura, sumy) that are absent from this environment;
stub them so the import chain resolves without installing anything.
"""

import sys
import types
from unittest.mock import MagicMock


def _stub_package(name, **attrs):
    module = types.ModuleType(name)
    module.__path__ = []
    for key, value in attrs.items():
        setattr(module, key, value)
    sys.modules[name] = module
    return module


if "scrapy" not in sys.modules:
    _scrapy = _stub_package(
        "scrapy",
        Spider=object,
        Request=object,
        http=types.SimpleNamespace(Response=object),
    )
    _stub_package("scrapy.crawler", CrawlerProcess=object)
    _stub_package("scrapy.http", Response=object)
    _stub_package("scrapy.utils")
    _stub_package("scrapy.utils.ossignal")
    _scrapy.utils = sys.modules["scrapy.utils"]

if "twisted" not in sys.modules:
    _stub_package("twisted")
    _stub_package("twisted.internet")
    _stub_package("twisted.internet._signals")
    _stub_package("twisted.python")
    _stub_package("twisted.python.failure", Failure=object)

if "trafilatura" not in sys.modules:
    _stub_package("trafilatura")
if "sumy" not in sys.modules:
    _stub_package("sumy")
    _stub_package("sumy.parsers")
    _stub_package("sumy.parsers.plaintext", PlaintextParser=object)
    _stub_package("sumy.nlp")
    _stub_package("sumy.nlp.tokenizers", Tokenizer=object)
    _stub_package("sumy.summarizers")
    _stub_package("sumy.summarizers.lsa", LsaSummarizer=object)

from airunner_services.llm.tools.intelligent_crawl_tool import (
    _send_crawler_decision,
)


def _patched_mediator(monkeypatch, mediator):
    import airunner_services.utils.application.signal_mediator as sm

    monkeypatch.setattr(sm, "SignalMediator", lambda: mediator)
    return mediator


def test_happy_path_returns_response_and_cleans_up(monkeypatch):
    mediator = _patched_mediator(monkeypatch, MagicMock())
    mediator.wait_for_response.return_value = {"response": "ok"}
    api = MagicMock()
    out = _send_crawler_decision(api, "prompt", MagicMock(), "DECISION", "req-1")
    assert out == {"response": "ok"}
    mediator.register_pending_request.assert_called_once_with("req-1")
    api.llm.send_request.assert_called_once()
    kwargs = api.llm.send_request.call_args[1]
    assert kwargs["do_tts_reply"] is False
    assert kwargs["request_id"] == "req-1"
    mediator.wait_for_response.assert_called_once_with("req-1", timeout=30.0)
    mediator.unregister_pending_request.assert_called_once_with("req-1")


def test_cleanup_runs_when_send_fails(monkeypatch):
    mediator = _patched_mediator(monkeypatch, MagicMock())
    api = MagicMock()
    api.llm.send_request.side_effect = RuntimeError("boom")
    try:
        _send_crawler_decision(api, "prompt", MagicMock(), "DECISION", "req-2")
    except RuntimeError:
        pass
    else:
        raise AssertionError("expected RuntimeError")
    mediator.unregister_pending_request.assert_called_once_with("req-2")


def test_cleanup_runs_when_wait_returns_none(monkeypatch):
    mediator = _patched_mediator(monkeypatch, MagicMock())
    mediator.wait_for_response.return_value = None
    out = _send_crawler_decision(MagicMock(), "p", MagicMock(), "DECISION", "req-3")
    assert out is None
    mediator.unregister_pending_request.assert_called_once_with("req-3")
