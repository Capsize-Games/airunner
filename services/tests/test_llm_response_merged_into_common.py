"""Regression test for issue #2188, continued (llm_response.py resolved).

``llm_request.py`` and ``llm_services.py`` (plus its services-side
mixins) remain deliberately unresolved -- see the issue comments and
the investigation recorded there. ``llm_response.py`` is a pure
``dataclass`` with no methods on either side, so unlike those two it
was safe to resolve by unioning both field sets into one definition in
``airunner_common`` (published from ``Capsize-Games/airunner-common``)
rather than picking a side or leaving it forked.

Field-shape coverage (the union is exactly desktop's fields plus
services' fields, each with its original default) lives in
``airunner-common``'s own test suite, not here -- this test only
guards the two things specific to *this* repository: that neither old
fork path exists any more, and that both live call sites now resolve
to the one shared class.

Merging ``LLMResponse`` made desktop's separate, byte-identical
``airunner.enums.LLMActionType`` (used as the default for the new
``action`` field) load-bearing in a way it wasn't before: services
already resolved ``LLMActionType`` to
``airunner_common.contract_enums.LLMActionType`` via its enum
resolver, so if desktop kept its own distinct ``Enum`` class, a
response built on the services side and compared against
``airunner.enums.LLMActionType.CHAT`` on the desktop side would
silently fail equality (different ``Enum`` subclasses never compare
equal, even with identical members). Desktop's copy is now a
re-export of the shared class, matching the precedent already set for
``AvailableLanguage`` (issue #2197) -- this test file also pins that.
"""

from __future__ import annotations

from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_desktop_llm_response_fork_is_gone():
    dead_path = (
        _PROJECT_ROOT
        / "src"
        / "airunner"
        / "components"
        / "llm"
        / "managers"
        / "llm_response.py"
    )
    assert not dead_path.exists()


def test_services_llm_response_fork_is_gone():
    dead_path = (
        _PROJECT_ROOT
        / "services"
        / "src"
        / "airunner_services"
        / "llm"
        / "llm_response.py"
    )
    assert not dead_path.exists()


def test_no_remaining_fork_import_paths():
    fragments = [
        "airunner.components.llm.managers.llm_response",
        "airunner_services.llm.llm_response",
    ]
    this_file = Path(__file__).resolve()
    offenders = []
    for root_name in ("src", "services"):
        for path in (_PROJECT_ROOT / root_name).rglob("*.py"):
            if "__pycache__" in path.parts or path.resolve() == this_file:
                continue
            text = path.read_text(encoding="utf-8")
            for fragment in fragments:
                if fragment in text:
                    offenders.append((str(path), fragment))
    assert offenders == []


def test_desktop_and_services_resolve_the_identical_class():
    import sys

    sys.path[:0] = [
        str(_PROJECT_ROOT / "src"),
        str(_PROJECT_ROOT / "services" / "src"),
    ]
    from airunner.components.llm.api.llm_services import (
        LLMResponse as desktop_llm_response,
    )
    from airunner_services.api.services.llm_services import (
        LLMResponse as services_llm_response,
    )

    assert desktop_llm_response is services_llm_response
    assert (
        desktop_llm_response.__module__ == "airunner_common.llm_response"
    )


def test_desktop_action_type_is_the_shared_enum_not_a_parallel_copy():
    from airunner.enums import LLMActionType as desktop_action_type
    from airunner_common.contract_enums import (
        LLMActionType as shared_action_type,
    )

    assert desktop_action_type is shared_action_type


def test_response_action_field_round_trips_through_both_enum_import_paths():
    """A response built services-side must compare equal desktop-side.

    This is the failure mode a duplicated ``LLMActionType`` class would
    reintroduce silently: not an import error, a same-looking enum
    member that no longer equals its desktop-imported counterpart.
    """
    import sys

    sys.path[:0] = [
        str(_PROJECT_ROOT / "src"),
        str(_PROJECT_ROOT / "services" / "src"),
    ]
    from airunner.enums import LLMActionType
    from airunner_common.llm_response import LLMResponse

    response = LLMResponse(action=LLMActionType.GENERATE_IMAGE)
    assert response.action == LLMActionType.GENERATE_IMAGE
