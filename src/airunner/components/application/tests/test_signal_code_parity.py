"""Wire-parity guard between the GUI and shared ``SignalCode`` enums.

Issue 101 established ``shared/airunner_common/contract_enums.py`` as the
single source of truth for cross-process signal wire values. The desktop GUI
(``src/``) intentionally keeps its own ``airunner.enums.SignalCode`` copy:
the GUI's ``SignalMediator`` dispatches by enum-member *identity*
(``code in self.signals`` in ``src/airunner/utils/application/
signal_mediator.py``), so a GUI component that mixed the two enum classes
would silently stop receiving its own events. The services daemon's mediator
is value-keyed, which is why ``services/`` imports the shared enum directly.

Both copies therefore must keep agreeing on the *wire values* of every member
they share by name — that value agreement is what keeps cross-process string
dispatch correct. These tests pin that invariant so drift cannot slip back in.
"""

from __future__ import annotations

import re
from pathlib import Path

from airunner.enums import SignalCode as GuiSignalCode
from airunner_common.contract_enums import SignalCode as SharedSignalCode

# Files converted in issue #201 ("narrow the string-typed signal bus at the
# hottest seams"). Their SignalCode references must all resolve on the GUI
# enum, because the GUI signal bus dispatches by enum-member identity.
# The test lives under src/airunner/components/application/tests/, so
# parents[3] is the src/airunner package directory.
_AIRUNNER_ROOT = Path(__file__).resolve().parents[3]
_CONVERTED_SEAM_FILES = (
    _AIRUNNER_ROOT / "components" / "llm" / "api" / "llm_services.py",
    _AIRUNNER_ROOT
    / "components"
    / "chat"
    / "gui"
    / "widgets"
    / "chat_prompt_widget.py",
    _AIRUNNER_ROOT
    / "components"
    / "chat"
    / "gui"
    / "widgets"
    / "conversation_widget.py",
)


def _member_values(enum_cls):
    return {member.name: member.value for member in enum_cls}


def test_shared_enum_is_imported_from_airunner_common():
    """The shared SignalCode really is the single shared source."""
    assert SharedSignalCode.__module__ == "airunner_common.contract_enums"


def test_gui_enum_is_a_deliberate_parallel_copy_not_the_shared_class():
    """The GUI keeps its own SignalCode; it is not a re-export.

    The GUI mediator dispatches by enum-member identity, so the GUI copy must
    remain a distinct class. If this ever becomes a re-export of the shared
    class, the identity-keyed GUI signal bus will silently stop routing events
    between GUI components that import the two different classes.
    """
    assert GuiSignalCode is not SharedSignalCode
    assert GuiSignalCode.__module__ == "airunner.enums"


def test_shared_and_gui_common_members_agree_on_value():
    """Every member name present in BOTH enums must carry the same value.

    Cross-process signal dispatch is value/string based, so a value mismatch
    on any name shared by both enums would break daemon-client signalling.
    The GUI enum legitimately has more members (GUI-only) and the shared enum
    has a few services-only members, but where they overlap the wire values
    must agree.
    """
    gui_values = _member_values(GuiSignalCode)
    shared_values = _member_values(SharedSignalCode)

    mismatches = {
        name: (gui_values[name], shared_values[name])
        for name in shared_values
        if name in gui_values and gui_values[name] != shared_values[name]
    }
    assert not mismatches, f"SignalCode wire-value drift: {mismatches}"


def test_converted_seam_files_only_reference_gui_present_signals():
    """Members referenced by the issue-201 seam files exist on the GUI enum.

    A reference to a member that exists only in the shared enum would raise
    ``AttributeError`` when the GUI imports its local copy, so every member
    these files touch must be present on ``airunner.enums.SignalCode``.
    """
    gui_members = set(GuiSignalCode.__members__)
    referenced = set()
    for path in _CONVERTED_SEAM_FILES:
        source = path.read_text(encoding="utf-8")
        referenced.update(
            re.findall(r"SignalCode\.([A-Za-z0-9_]+)", source)
        )
    assert referenced, "No SignalCode references found in seam files"
    missing = sorted(referenced - gui_members)
    assert not missing, (
        "Seam files reference SignalCode members missing from the GUI "
        f"enum: {missing}"
    )
