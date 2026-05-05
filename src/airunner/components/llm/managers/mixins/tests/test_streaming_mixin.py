"""Unit tests for StreamingMixin."""

from types import SimpleNamespace


from airunner.components.llm.managers.mixins.streaming_mixin import (
    CODE_WORKFLOW_RECURSION_LIMIT,
    DEFAULT_WORKFLOW_RECURSION_LIMIT,
    StreamingMixin,
)


class TestableStreamingMixin(StreamingMixin):
    """Minimal StreamingMixin harness for config tests."""

    def __init__(self):
        self._thread_id = "thread-1"
        self.llm_request = None


def test_create_config_uses_default_recursion_limit():
    """Non-code requests should keep the default workflow budget."""
    mixin = TestableStreamingMixin()

    config = mixin._create_config()

    assert config["configurable"]["thread_id"] == "thread-1"
    assert config["recursion_limit"] == DEFAULT_WORKFLOW_RECURSION_LIMIT


def test_create_config_uses_higher_recursion_limit_for_code_tools():
    """Code requests should get extra graph budget for validation turns."""
    mixin = TestableStreamingMixin()
    mixin.llm_request = SimpleNamespace(
        tool_categories=["CODE", "WORKFLOW", "SYSTEM"],
        mode_override=None,
    )

    config = mixin._create_config()

    assert config["recursion_limit"] == CODE_WORKFLOW_RECURSION_LIMIT