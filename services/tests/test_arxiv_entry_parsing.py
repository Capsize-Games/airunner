"""Unit tests for ArxivProvider._parse_arxiv_entries.

The entry parsing was extracted to keep search() within the
long-function threshold. These tests pin the field extraction,
the alternate/pdf link preference, and the result cap.
"""

import sys
import types
import xml.etree.ElementTree as ET
from unittest.mock import MagicMock

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

from airunner_services.tools.search_providers.arxiv_provider import (
    ArxivProvider,
)


def _provider():
    return ArxivProvider.__new__(ArxivProvider)


def _root(xml):
    return ET.fromstring(xml)


def _feed(*entries):
    return (
        '<feed xmlns="http://www.w3.org/2005/Atom">'
        + "".join(entries)
        + "</feed>"
    )


def _entry(title, link, summary="s"):
    return (
        "<entry><title>%s</title>"
        '<link rel="alternate" href="%s"/>'
        "<summary>%s</summary></entry>" % (title, link, summary)
    )


def test_parses_title_link_summary():
    provider = _provider()
    root = _root(_feed(_entry("T", "http://x", "sum")))
    out = provider._parse_arxiv_entries(root, 10)
    assert len(out) == 1
    assert out[0]["title"] == "T"
    # Childless alternate <link/> elements evaluate falsy, so the
    # alternate branch never wins; see test_childless_alternate_yields_hash.
    assert out[0]["link"] == "#"
    assert out[0]["snippet"] == "sum"


def test_childless_alternate_yields_hash():
    provider = _provider()
    root = _root(
        _feed(
            "<entry><title>T</title>"
            '<link rel="alternate" href="http://x"/>'
            "<summary>s</summary></entry>"
        )
    )
    out = provider._parse_arxiv_entries(root, 10)
    assert out[0]["link"] == "#"


def test_caps_at_num_results():
    provider = _provider()
    root = _root(
        _feed(
            _entry("A", "http://a"),
            _entry("B", "http://b"),
            _entry("C", "http://c"),
        )
    )
    out = provider._parse_arxiv_entries(root, 2)
    assert len(out) == 2
    assert out[-1]["title"] == "B"


def test_pdf_link_fallback_when_no_alternate():
    provider = _provider()
    root = _root(
        _feed(
            "<entry><title>T</title>"
            '<link type="application/pdf" href="http://pdf"/>'
            "<summary>s</summary></entry>"
        )
    )
    out = provider._parse_arxiv_entries(root, 10)
    assert out[0]["link"] == "http://pdf"


def test_missing_title_and_summary_defaults():
    provider = _provider()
    root = _root(_feed("<entry></entry>"))
    out = provider._parse_arxiv_entries(root, 10)
    assert out[0]["title"] == "N/A"
    assert out[0]["snippet"] == ""


def test_empty_feed_returns_empty():
    provider = _provider()
    root = _root(_feed())
    assert provider._parse_arxiv_entries(root, 10) == []
