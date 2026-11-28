"""Unit tests for web_tools._format_news_results.

The summary rendering was extracted to keep search_news within the
long-function threshold. These tests pin the numbered layout, the
snippet truncation, the result cap, and the next-steps footer.
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


if "ddgs" not in sys.modules:
    try:
        import ddgs  # noqa: F401
    except ImportError:
        _ddgs = types.ModuleType("ddgs")
        _ddgs.DDGS = object
        sys.modules["ddgs"] = _ddgs
if "duckduckgo_search" not in sys.modules:
    try:
        import duckduckgo_search  # noqa: F401
    except ImportError:
        _duck = types.ModuleType("duckduckgo_search")
        _duck.DDGS = object
        sys.modules["duckduckgo_search"] = _duck

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

from airunner_services.tools.web_tools import _format_news_results


def test_single_result_layout():
    out = _format_news_results(
        "q",
        [
            {
                "title": "T",
                "link": "http://x",
                "snippet": "snip",
                "source": "BBC",
                "date": "2024-01-01",
            }
        ],
    )
    assert "1. T" in out
    assert "Source: BBC | Date: 2024-01-01" in out
    assert "URL: http://x" in out
    assert "snip..." in out
    assert "NEXT STEPS" in out


def test_defaults_for_missing_fields():
    out = _format_news_results("q", [{}])
    assert "N/A" in out
    assert "#" in out
    assert "Unknown source" in out


def test_snippet_truncated_at_250():
    out = _format_news_results("q", [{"snippet": "x" * 300}])
    assert "x" * 250 + "..." in out
    assert "x" * 251 not in out


def test_caps_at_seven_results():
    results = [{"title": f"T{i}"} for i in range(10)]
    out = _format_news_results("q", results)
    assert "7. T6" in out
    assert "8." not in out


def test_no_date_omits_date_segment():
    out = _format_news_results("q", [{"title": "T", "source": "S"}])
    assert " | Date:" not in out
    assert "Source: S" in out
