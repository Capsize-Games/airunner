"""Unit tests for the tool-wrapper extraction helpers.

_inspect_tool_signature and _merge_request_defaults were extracted
to keep _wrap_tool_with_dependencies within the long-function
threshold. These tests pin the signature classification and the
default-merging rules.
"""

from types import SimpleNamespace
from unittest.mock import MagicMock

from airunner_services.llm.tool_manager import ToolManager


def _info(func):
    return SimpleNamespace(func=func)


def test_inspect_classifies_named_params():
    def tool(query, api, extra=None):
        ...

    sig, accepted, var_kwargs, visible = ToolManager._inspect_tool_signature(
        _info(tool)
    )
    assert sig is not None
    assert accepted == {"query", "api", "extra"}
    assert var_kwargs is False
    assert [p.name for p in visible] == ["query", "extra"]


def test_inspect_detects_var_kwargs():
    def tool(**kwargs):
        ...

    sig, accepted, var_kwargs, visible = ToolManager._inspect_tool_signature(
        _info(tool)
    )
    assert var_kwargs is True
    assert accepted == set()


def test_inspect_broken_signature_returns_nones():
    sig, accepted, var_kwargs, visible = ToolManager._inspect_tool_signature(
        _info(None)
    )
    assert sig is None
    assert accepted == set()
    assert var_kwargs is False
    assert visible == []


def _make_manager(defaults):
    manager = ToolManager.__new__(ToolManager)
    manager._request_tool_defaults = defaults
    return manager


def test_merge_defaults_applies_accepted_keys_only():
    manager = _make_manager({"topic": "ai", "unknown": 1, "none_val": None})
    kwargs = {}
    manager._merge_request_defaults(object(), False, {"topic"}, kwargs)
    assert kwargs == {"topic": "ai"}


def test_merge_defaults_var_kwargs_accepts_anything():
    manager = _make_manager({"anything": 5})
    kwargs = {}
    manager._merge_request_defaults(object(), True, set(), kwargs)
    assert kwargs == {"anything": 5}


def test_merge_defaults_never_overrides_caller_values():
    manager = _make_manager({"topic": "ai"})
    kwargs = {"topic": "caller"}
    manager._merge_request_defaults(object(), True, {"topic"}, kwargs)
    assert kwargs == {"topic": "caller"}


def test_merge_defaults_noop_without_sig_or_var():
    manager = _make_manager({"topic": "ai"})
    kwargs = {}
    manager._merge_request_defaults(None, False, set(), kwargs)
    assert kwargs == {}
