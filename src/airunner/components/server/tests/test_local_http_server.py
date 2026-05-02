"""Tests for local HTTP static asset caching rules."""

from airunner.components.server.local_http_server import (
    should_disable_cache_for_static_file,
)


def test_should_disable_cache_for_static_file_covers_web_assets():
    """JS and CSS assets should bypass cache to avoid stale webviews."""
    assert should_disable_cache_for_static_file("conversation.css")
    assert should_disable_cache_for_static_file("conversation.js")
    assert not should_disable_cache_for_static_file("conversation.png")