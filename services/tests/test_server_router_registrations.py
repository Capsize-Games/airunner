"""Unit tests for the router registration table.

_register_routers was converted to a data-driven loop over
_ROUTER_REGISTRATIONS to keep it within the long-function threshold.
These tests pin the registration count, order, and tags.
"""

from unittest.mock import MagicMock

from airunner_services.api import server as server_module


def test_registers_every_router_in_order():
    app = MagicMock()
    server_module._register_routers(app)
    prefixes = [
        call.kwargs.get("prefix") for call in app.include_router.call_args_list
    ]
    assert prefixes == [
        "/api/v1",
        "/api/v1/daemon",
        "/api/v1/llm",
        "/api/v1/llm",
        "/api/v1/state",
        "/api/v1/persistence",
        "/api/v1/settings",
        "/api/v1/catalog",
        "/api/v1/catalog",
        "/api/v1/library",
        "/api/v1/workspace",
        "/api/v1/art",
        "/api/v1/video",
        "/api/v1/downloads",
        "/api/v1",
        "/api/v1/tts",
        "/api/v1/tts",
        "/api/v1/stt",
        "/api/v1",
        None,  # legacy, no prefix
    ]


def test_tags_match_registrations():
    app = MagicMock()
    server_module._register_routers(app)
    tagged = [
        call.kwargs["tags"]
        for call in app.include_router.call_args_list
        if call.kwargs.get("tags")
    ]
    assert tagged[0] == ["health"]
    assert ["llm", "conversations"] in tagged
    assert tagged[-1] == ["legacy"]


def test_catalog_routers_share_prefix():
    prefixes = [prefix for _, prefix, _ in server_module._ROUTER_REGISTRATIONS]
    catalog = [p for p in prefixes if p == "/api/v1/catalog"]
    assert len(catalog) == 2
