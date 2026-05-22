"""Unit tests for the shared consciousness integration helper."""

from unittest.mock import Mock

from airunner.components.llm.managers.mixins.node_functions import (
    ConsciousnessIntegrationMixin,
)


class _TestableConsciousnessIntegrationMixin(
    ConsciousnessIntegrationMixin
):
    """Minimal harness for shared consciousness helper tests."""

    def __init__(self):
        self.data = {}
        self._conversation_id = 42
        self._thread_id = "thread-1"
        self.engine = None

    def _get_consciousness_engine(self):
        return self.engine


def test_run_consciousness_hook_passes_context():
    """Shared hook runner should pass the generated context object."""
    mixin = _TestableConsciousnessIntegrationMixin()
    mixin.engine = Mock()

    mixin._run_consciousness_hook(
        "on_pre_turn",
        messages=["hello"],
    )

    mixin.engine.on_pre_turn.assert_called_once()
    context = mixin.engine.on_pre_turn.call_args.args[0]
    assert context.conversation_id == 42
    assert context.thread_id == "thread-1"
    assert context.messages == ["hello"]


def test_run_consciousness_hook_respects_disable_flag():
    """Disabled requests should not call the optional engine."""
    mixin = _TestableConsciousnessIntegrationMixin()
    mixin.data = {"enable_consciousness": "false"}
    mixin.engine = Mock()

    mixin._run_consciousness_hook(
        "on_post_llm",
        object(),
        messages=["hello"],
    )

    mixin.engine.on_post_llm.assert_not_called()