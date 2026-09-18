"""Regression test for issue #2221 (LLMRequest fields now shared).

Desktop's ``src/airunner/components/llm/managers/llm_request.py`` and
services' ``services/src/airunner_services/llm/llm_request.py`` keep
their own classmethods (``from_chatbot``/``from_llm_settings``/
``for_action`` and two different serialization targets), but they no
longer each re-declare the *fields* they have in common: those live once
in ``airunner_common.llm_request.LLMRequest`` and both sides subclass it.

Two things this test exists to protect, both of which a plain
"the tests still pass" run would not catch:

1. **The two sides must resolve to the same base class** -- otherwise the
   shared fields have silently re-forked.
2. **Each side must NOT gain the other's private fields.** Services'
   legacy API layer copies untrusted request input through a
   ``hasattr(llm_request, key)`` filter and its request model sets
   ``extra="allow"``; if the desktop-only planning fields were unioned
   into the shared base, an external API caller could start injecting
   them into a services request (see #2221). This test pins that services
   still lacks the desktop-only attributes, and desktop still lacks the
   services-only ones.

The field-by-field shape of the shared class lives in ``airunner-common``'s
own suite; the before/after proof that ``to_dict()``'s wire output did not
change lives in #2221 itself.
"""

from __future__ import annotations

import dataclasses
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]

_DESKTOP_PRIVATE_FIELDS = {
    "final_system_prompt",
    "rewritten_prompt",
    "preprocessed_primary_tool",
    "planner_mode",
    "planner_tool_hints",
    "attached_document_capabilities",
    "attached_document_total_tokens",
    "attached_document_total_characters",
    "document_query_intent",
    "document_summary_focus",
    "document_primary_tool",
    "document_answer_mode",
    "request_plan",
}
_SERVICES_PRIVATE_FIELDS = {
    "gguf_runtime_profile",
    "client_tools",
    "client_tool_choice",
    "raw_mode",
}

# The exact key set desktop's to_dict() produced before the merge, i.e.
# the payload gui_daemon_client.py sends to /llm/generate. Pinned so a
# future field-union mistake can't leak a new key onto the live wire.
_WIRE_KEYS = {
    "do_sample",
    "eta_cutoff",
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
    "do_tts_reply",
    "ephemeral",
    "tool_categories",
    "system_prompt",
    "response_format",
    "rag_files",
    "ephemeral_conversation",
    "enable_thinking",
    "model",
    "force_tool",
}


def _classes():
    import sys

    sys.path[:0] = [
        str(_PROJECT_ROOT / "src"),
        str(_PROJECT_ROOT / "services" / "src"),
    ]
    from airunner.components.llm.managers.llm_request import (
        LLMRequest as DesktopLLMRequest,
    )
    from airunner_services.llm.llm_request import (
        LLMRequest as ServicesLLMRequest,
    )
    from airunner_common.llm_request import LLMRequest as SharedLLMRequest

    return DesktopLLMRequest, ServicesLLMRequest, SharedLLMRequest


def test_both_sides_subclass_the_identical_shared_base():
    desktop, services, shared = _classes()
    assert desktop.__mro__[1] is shared
    assert services.__mro__[1] is shared


def test_desktop_keeps_only_its_private_fields_plus_the_shared_set():
    desktop, _, shared = _classes()
    shared_names = {f.name for f in dataclasses.fields(shared)}
    desktop_names = {f.name for f in dataclasses.fields(desktop)}
    assert desktop_names == shared_names | _DESKTOP_PRIVATE_FIELDS


def test_services_keeps_only_its_private_fields_plus_the_shared_set():
    _, services, shared = _classes()
    shared_names = {f.name for f in dataclasses.fields(shared)}
    services_names = {f.name for f in dataclasses.fields(services)}
    assert services_names == shared_names | _SERVICES_PRIVATE_FIELDS


def test_services_request_does_not_gain_desktop_private_attributes():
    """Guards the legacy ``hasattr``-filter input surface (see docstring)."""
    _, services, _ = _classes()
    request = services()
    for name in _DESKTOP_PRIVATE_FIELDS:
        assert not hasattr(request, name), (
            f"services LLMRequest unexpectedly gained {name!r}; this would "
            "change what legacy_llm_helpers._populate_llm_fields accepts"
        )


def test_desktop_request_does_not_gain_services_private_attributes():
    desktop, _, _ = _classes()
    request = desktop()
    for name in _SERVICES_PRIVATE_FIELDS:
        assert not hasattr(
            request, name
        ), f"desktop LLMRequest unexpectedly gained {name!r}"


def test_desktop_to_dict_wire_keys_are_unchanged():
    desktop, _, _ = _classes()
    assert set(desktop().to_dict()) == _WIRE_KEYS


def test_message_role_is_one_shared_class_across_every_import_path():
    from airunner.enums import MessageRole as desktop_role
    from airunner_services.runtimes.contracts import (
        MessageRole as services_role,
    )
    from airunner_common.contract_enums import (
        MessageRole as shared_role,
    )

    assert desktop_role is shared_role
    assert services_role is shared_role


def test_role_default_is_the_shared_member_on_both_sides():
    from airunner_common.contract_enums import MessageRole

    desktop, services, _ = _classes()
    assert desktop().role is MessageRole.USER
    assert services().role is MessageRole.USER
