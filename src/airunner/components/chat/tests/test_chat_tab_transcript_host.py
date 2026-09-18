"""Guards the chat tab's transcript host (#2230, B4a).

The generated chat prompt template must fill the transcript slot with the
hosted chat surface. Reverting that to a Qt-rendered transcript would
silently remove the app's chat surface, so the generated source is
asserted here.
"""

from __future__ import annotations

import inspect

from airunner.components.chat.gui.widgets.templates.chat_prompt_ui import (
    Ui_chat_prompt,
)


def test_chat_prompt_template_hosts_the_chat_surface() -> None:
    """The transcript slot is filled with the hosted surface widget."""
    source = inspect.getsource(Ui_chat_prompt.setupUi)
    assert "ChatSurfaceWidget(self.splitter)" in source


def test_chat_prompt_template_no_longer_builds_a_qt_transcript() -> None:
    """The removed Qt transcript widget is not referenced any more."""
    source = inspect.getsource(Ui_chat_prompt.setupUi)
    assert "ConversationWidget" not in source
