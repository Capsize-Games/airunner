"""Regression test for issue #2225 (for_action presets unified).

Before #2225, desktop ``LLMRequest.for_action()`` (delegating to
``airunner.components.llm.config.generation_presets``) and services'
independently-inlined ladder resolved 13 of the 20 ``LLMActionType``
members to different effective generation kwargs -- chat/mood at 0.2 vs
0.7, RAG/search/summarize at 0.2 vs 0.3, and unmapped actions meaning
"all tools" (``None``) vs "no tools" (``[]``).

The two implementations now call one shared table in
``airunner_common.generation_presets``. This test pins three things a
plain "the tests still pass" run would not catch:

1. Both sides resolve to the *same* preset object for every action.
2. Every compared generation field agrees between the two live code
   paths (the same measurement ``scripts/compare_llm_request_for_action.py``
   performs, kept as a unit test so it runs in the normal suite).
3. Desktop's ``generation_presets`` module still re-exports the shared
   table rather than growing a private copy again.

The exact values themselves are pinned in ``airunner-common``'s own
``tests/test_generation_presets.py``; this test only guards parity.
"""

from __future__ import annotations

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [
    str(_PROJECT_ROOT / "src"),
    str(_PROJECT_ROOT / "services" / "src"),
]

# Effective generation fields, i.e. everything either for_action() table
# can influence -- kept in sync with scripts/compare_llm_request_for_action.py.
_COMPARED_FIELDS = (
    "do_sample",
    "early_stopping",
    "eta_cutoff",
    "length_penalty",
    "max_new_tokens",
    "min_length",
    "no_repeat_ngram_size",
    "num_beams",
    "num_return_sequences",
    "repetition_penalty",
    "temperature",
    "top_k",
    "top_p",
    "use_cache",
    "tool_categories",
    "reasoning_effort",
)


def _imports():
    from airunner.components.llm.managers.llm_request import (
        LLMRequest as DesktopLLMRequest,
    )
    from airunner_services.llm.llm_request import (
        LLMRequest as ServicesLLMRequest,
    )
    from airunner_common.contract_enums import LLMActionType

    return DesktopLLMRequest, ServicesLLMRequest, LLMActionType


def _snapshot(request: object) -> dict:
    return {name: getattr(request, name, None) for name in _COMPARED_FIELDS}


def test_every_action_resolves_to_the_same_effective_generation_kwargs():
    desktop_cls, services_cls, action_type = _imports()
    for action in action_type:
        desktop = _snapshot(desktop_cls.for_action(action))
        services = _snapshot(services_cls.for_action(action))
        diffs = {
            name: (desktop[name], services[name])
            for name in _COMPARED_FIELDS
            if desktop[name] != services[name]
        }
        assert not diffs, (
            f"{action.name} diverges between desktop and services "
            f"for_action(): {diffs}"
        )


def test_both_sides_delegate_to_the_same_shared_table():
    desktop_cls, services_cls, action_type = _imports()
    from airunner_common.generation_presets import get_action_generation_preset

    for action in action_type:
        shared = get_action_generation_preset(action)
        assert desktop_cls.for_action(action).tool_categories == (
            list(shared.tool_categories) if shared.tool_categories else None
        )
        assert services_cls.for_action(action).tool_categories == (
            list(shared.tool_categories) if shared.tool_categories else None
        )


def test_desktop_preset_module_reexports_the_shared_table():
    """Guards against desktop re-growing a private fork of the table."""
    from airunner.components.llm.config import (
        generation_presets as desktop_mod,
    )
    from airunner_common import generation_presets as shared_mod

    assert desktop_mod.ACTION_GENERATION_PRESETS is (
        shared_mod.ACTION_GENERATION_PRESETS
    )
    assert (
        desktop_mod.DEFAULT_ACTION_PRESET is shared_mod.DEFAULT_ACTION_PRESET
    )
    assert desktop_mod.get_action_generation_preset is (
        shared_mod.get_action_generation_preset
    )


def test_services_for_action_has_no_inline_preset_ladder():
    """The inline ladder must be gone, not merely shadowed (#2225)."""
    import inspect

    from airunner_services.llm.llm_request import LLMRequest

    source = inspect.getsource(LLMRequest.for_action)
    assert "get_action_generation_preset(action)" in source
    # The stale services-only value that used to be hard-coded here.
    assert "temperature=0.7" not in source
