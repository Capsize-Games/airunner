"""Unit tests for the web extractor extraction helpers.

_url_admissible_for_extract, _cached_extraction_result, and
_extract_html_metadata were extracted to keep
fetch_and_extract_with_metadata_raw within the long-function
threshold. These tests pin the policy gates, the cache forms, and
the metadata assembly.
"""

import sys
import types


def _stub_package(name, **attrs):
    module = types.ModuleType(name)
    module.__path__ = []
    for key, value in attrs.items():
        setattr(module, key, value)
    sys.modules[name] = module
    return module


if "scrapy" not in sys.modules:
    _scrapy = _stub_package("scrapy", Spider=object, Request=object)
    _stub_package("scrapy.crawler", CrawlerProcess=object)
    _stub_package("scrapy.http", Response=object)
    _stub_package("scrapy.utils")
    _stub_package("scrapy.utils.ossignal")
    _scrapy.utils = sys.modules["scrapy.utils"]
    _scrapy.http = sys.modules["scrapy.http"]

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

from airunner_services.tools.web_content_extractor import WebContentExtractor as WCE


def test_admissible_when_policy_and_blocklist_pass(monkeypatch):
    import airunner_services.tools.web_content_extractor as ext_mod

    monkeypatch.setattr(ext_mod, "validate_url_for_fetch", lambda url: None)
    monkeypatch.setattr(
        WCE, "_is_blocked", staticmethod(lambda url: False)
    )
    assert WCE._url_admissible_for_extract("https://example.com/x") is True


def test_inadmissible_when_domain_blocked(monkeypatch):
    import airunner_services.tools.web_content_extractor as ext_mod

    monkeypatch.setattr(ext_mod, "validate_url_for_fetch", lambda url: None)
    monkeypatch.setattr(WCE, "_is_blocked", staticmethod(lambda url: True))
    assert WCE._url_admissible_for_extract("https://bad.example/x") is False


def test_cached_summarized_form_returned(monkeypatch):
    monkeypatch.setattr(
        WCE,
        "get_cached_metadata",
        classmethod(lambda cls, url: {"content": "sum", "title": "t"}),
    )
    out = WCE._cached_extraction_result("https://x", summarize=True)
    assert out == {"content": "sum", "title": "t"}


def test_cached_raw_form_renames_key(monkeypatch):
    monkeypatch.setattr(
        WCE,
        "get_cached_metadata",
        classmethod(lambda cls, url: {"raw_content": "raw", "title": "t"}),
    )
    out = WCE._cached_extraction_result("https://x", summarize=False)
    assert out == {"content": "raw", "title": "t"}


def test_cached_miss_returns_none(monkeypatch):
    monkeypatch.setattr(
        WCE, "get_cached_metadata", classmethod(lambda cls, url: None)
    )
    assert WCE._cached_extraction_result("https://x", summarize=False) is None


def test_extract_html_assembles_metadata(monkeypatch):
    monkeypatch.setattr(
        sys.modules["trafilatura"],
        "extract",
        lambda html, **kw: "main text", raising=False
    )
    monkeypatch.setattr(
        sys.modules["trafilatura"],
        "extract_metadata",
        lambda html: type("M", (), {"title": "T", "description": "D", "author": "A", "date": None})(), raising=False
    )
    monkeypatch.setattr(
        WCE, "_summarize_text", staticmethod(lambda text: "summ: " + text)
    )
    out = WCE._extract_html_metadata("https://x", "<html/>", True, False)
    assert out["content"] == "summ: main text"
    assert out["title"] == "T"
    assert out["description"] == "D"
    assert out["author"] == "A"
    assert out["publish_date"] is None


def test_extract_html_raw_mode_keeps_main_text(monkeypatch):
    monkeypatch.setattr(
        sys.modules["trafilatura"],
        "extract",
        lambda html, **kw: "main text", raising=False
    )
    monkeypatch.setattr(
        sys.modules["trafilatura"],
        "extract_metadata",
        lambda html: None, raising=False
    )
    monkeypatch.setattr(
        WCE, "_summarize_text", staticmethod(lambda text: "summ")
    )
    out = WCE._extract_html_metadata("https://x", "<html/>", False, False)
    assert out["content"] == "main text"
    assert out["title"] is None
