"""Regression test for issue #2225 (for_action presets unified).

The desktop ``LLMRequest.for_action()`` side of this parity was removed
with the desktop client; the services implementation delegates to the
shared table in ``airunner_common.generation_presets``. This test keeps
the services-side pins: ``for_action`` must delegate to the shared
table rather than re-growing an inline preset ladder.

The exact values themselves are pinned in ``airunner-common``'s own
``tests/test_generation_presets.py``.
"""

from __future__ import annotations


def test_services_for_action_has_no_inline_preset_ladder():
    """The inline ladder must be gone, not merely shadowed (#2225)."""
    import inspect

    from airunner_services.llm.llm_request import LLMRequest

    source = inspect.getsource(LLMRequest.for_action)
    assert "get_action_generation_preset(action)" in source
    # The stale services-only value that used to be hard-coded here.
    assert "temperature=0.7" not in source
