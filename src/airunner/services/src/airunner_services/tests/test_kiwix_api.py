"""Tests for the service-owned Kiwix catalog client."""

from airunner_services.kiwix_api import KiwixAPI


_ATOM_FEED = """<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <id>wikipedia_en_all_maxi_2024-01</id>
    <title>Wikipedia EN</title>
    <summary>English Wikipedia snapshot</summary>
    <updated>2024-01-01T00:00:00Z</updated>
    <link rel="http://opds-spec.org/image/thumbnail" href="/covers/wiki.png" />
    <link rel="http://opds-spec.org/acquisition/open-access" href="https://download.kiwix.org/zim/wikipedia_en_all_maxi_2024-01.zim.meta4" />
  </entry>
</feed>
"""


def test_list_zim_files_builds_query_and_parses_entries(monkeypatch) -> None:
    captured = {}

    def fake_fetch(url: str, *, timeout_seconds: float = 15) -> str:
        captured["url"] = url
        captured["timeout_seconds"] = timeout_seconds
        return _ATOM_FEED

    monkeypatch.setattr(
        "airunner_services.kiwix_api.safe_fetch_url",
        fake_fetch,
    )

    entries = KiwixAPI.list_zim_files(language="eng", query="wikipedia")

    assert captured == {
        "url": (
            "https://browse.library.kiwix.org/catalog/v2/entries"
            "?lang=eng&q=wikipedia"
        ),
        "timeout_seconds": 15,
    }
    assert entries == [
        {
            "id": "wikipedia_en_all_maxi_2024-01",
            "title": "Wikipedia EN",
            "summary": "English Wikipedia snapshot",
            "updated": "2024-01-01T00:00:00Z",
            "name": "",
            "category": "",
            "image_url": "/covers/wiki.png",
            "url": (
                "https://download.kiwix.org/zim/"
                "wikipedia_en_all_maxi_2024-01.zim"
            ),
        }
    ]


def test_list_zim_files_returns_empty_list_on_fetch_error(monkeypatch) -> None:
    def fake_fetch(url: str, *, timeout_seconds: float = 15) -> str:
        del url, timeout_seconds
        raise RuntimeError("boom")

    monkeypatch.setattr(
        "airunner_services.kiwix_api.safe_fetch_url",
        fake_fetch,
    )

    assert KiwixAPI.list_zim_files(query="wikipedia") == []