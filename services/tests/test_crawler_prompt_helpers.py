"""Unit tests for the crawler decision-prompt helpers.

_content_preview and _format_links_section were extracted to keep
_format_decision_prompt within the long-function threshold. These
tests pin the truncation, numbering, and overflow behaviors.
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
    _scrapy.crawler = sys.modules["scrapy.crawler"]

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

from airunner_services.tools.scrapy.llm_crawler_controller import (
    LLMCrawlerController,
)


def _link(url, anchor="A", context="C"):
    return {"url": url, "anchor_text": anchor, "context": context}


def test_content_preview_short_content_unchanged():
    assert LLMCrawlerController._content_preview("abc") == "abc"


def test_content_preview_truncates_at_1000():
    long_text = "x" * 1500
    out = LLMCrawlerController._content_preview(long_text)
    assert out == "x" * 1000 + "..."


def test_content_preview_exact_limit_no_ellipsis():
    content = "y" * 1000
    assert LLMCrawlerController._content_preview(content) == content


def test_links_section_numbered():
    out = LLMCrawlerController._format_links_section(
        [_link("http://a", "A1", "C1"), _link("http://b", "A2", "C2")]
    )
    assert "1. http://a" in out and "Anchor: A1" in out
    assert "2. http://b" in out and "Context: C2" in out


def test_links_section_caps_at_ten_shown():
    links = [_link(f"http://{i}") for i in range(12)]
    out = LLMCrawlerController._format_links_section(links)
    assert "10. http://9" in out
    assert "11." not in out
    assert "2 more links (not shown)" in out


def test_links_section_empty():
    assert LLMCrawlerController._format_links_section([]) == ""
