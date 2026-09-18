#!/usr/bin/env python3
"""Compare desktop vs services ``LLMRequest.for_action()`` presets.

Empirical parity check for issue Capsize-Games/airunner#2225 (the
``for_action()`` reconciliation split out of #2221).

When this was written, ``for_action()`` existed on both forks with
independently-authored generation-preset tables:

* desktop routed through
  ``airunner.components.llm.config.generation_presets``
  (``ACTION_GENERATION_PRESETS`` + ``DEFAULT_ACTION_PRESET``),
* services inlined the same decision inside
  ``airunner_services.llm.llm_request.LLMRequest.for_action``.

This script ran the *actual* code paths (not a reading pass) for every
``LLMActionType`` member and measured that 13 of 20 agreed. #2225 then
unified both sides onto one table in ``airunner_common.generation_presets``
(desktop re-exports it; services calls
``get_action_generation_preset()``), so this script is now the CI gate
that proves they can never silently diverge again.

Usage::

    venv/bin/python scripts/compare_llm_request_for_action.py

Exit code is 0 when every action agrees and 1 when any differs. It is
wired into CI (``.github/workflows/eval-tests.yml``) as a regression
gate.
"""

from __future__ import annotations

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [
    str(_PROJECT_ROOT / "src"),
    str(_PROJECT_ROOT / "services" / "src"),
]

from airunner.components.llm.managers.llm_request import (  # noqa: E402
    LLMRequest as DesktopLLMRequest,
)
from airunner_services.llm.llm_request import (  # noqa: E402
    LLMRequest as ServicesLLMRequest,
)
from airunner_common.contract_enums import LLMActionType  # noqa: E402

# Effective generation fields, i.e. everything either ``for_action()``
# table can influence. Routing/book-keeping fields are out of scope;
# this is strictly the sampling behaviour an end user would notice.
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


def _snapshot(request: object) -> dict:
    return {name: getattr(request, name, None) for name in _COMPARED_FIELDS}


def main() -> int:
    divergences: list[tuple[str, dict]] = []
    for action in LLMActionType:
        desktop = _snapshot(DesktopLLMRequest.for_action(action))
        services = _snapshot(ServicesLLMRequest.for_action(action))
        diffs = {
            name: (desktop[name], services[name])
            for name in _COMPARED_FIELDS
            if desktop[name] != services[name]
        }
        label = "DIVERGES" if diffs else "agrees"
        print(f"{action.name:<24} {label}")
        for name, (desktop_value, services_value) in diffs.items():
            print(
                f"    {name}: desktop={desktop_value!r} "
                f"services={services_value!r}"
            )
        if diffs:
            divergences.append((action.name, diffs))

    print()
    if divergences:
        print(
            f"{len(divergences)}/{len(list(LLMActionType))} actions diverge "
            "between the desktop and services preset tables."
        )
        return 1
    print("All actions agree between the desktop and services preset tables.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
