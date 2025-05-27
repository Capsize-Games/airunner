"""
Robust test suite for PromptTemplatesWidget covering initialization, template switching, and prompt editing.
"""

import pytest
from unittest.mock import patch, MagicMock
from airunner.gui.widgets.llm import prompt_templates_widget


@pytest.fixture
def mock_templates():
    # Create mock PromptTemplate objects
    template1 = MagicMock()
    template1.template_name = "chatbot"
    template1.system = "sys1"
    template1.guardrails = "guard1"
    template1.use_guardrails = True
    template1.use_system_datetime_in_system_prompt = False
    template2 = MagicMock()
    template2.template_name = "image"
    template2.system = "sys2"
    template2.guardrails = "guard2"
    template2.use_guardrails = False
    template2.use_system_datetime_in_system_prompt = True
    return [template1, template2]


@pytest.fixture
def widget(qtbot, mock_templates):
    with patch(
        "airunner.data.models.PromptTemplate.objects.all",
        return_value=mock_templates,
    ):
        w = prompt_templates_widget.PromptTemplatesWidget()
        qtbot.addWidget(w)
        w.show()
        return w


def test_initializes_with_templates(widget, mock_templates):
    # Should populate combo box with template names
    names = [mock_templates[0].template_name, mock_templates[1].template_name]
    for i, name in enumerate(names):
        assert widget.ui.template_name.itemText(i) == name
    assert widget.current_template_index == 0


def test_template_changed_updates_ui(widget, mock_templates):
    # Simulate changing to second template
    widget.template_changed(1)
    t = mock_templates[1]
    assert widget.current_template_index == 1
    assert widget.ui.system_prompt.toPlainText() == t.system
    assert widget.ui.guardrails_prompt.toPlainText() == t.guardrails
    assert widget.ui.use_guardrails.isChecked() == t.use_guardrails
    assert widget.ui.use_datetime.isChecked() == t.use_system_datetime_in_system_prompt


def test_system_prompt_changed_saves(widget, mock_templates):
    widget.current_template_index = 0
    widget.ui.system_prompt.setPlainText("new system prompt")
    widget.system_prompt_changed()
    t = mock_templates[0]
    assert t.system == "new system prompt"
    assert t.save.called


def test_guardrails_prompt_changed_saves(widget, mock_templates):
    widget.current_template_index = 1
    widget.ui.guardrails_prompt.setPlainText("new guardrails")
    widget.guardrails_prompt_changed()
    t = mock_templates[1]
    assert t.guardrails == "new guardrails"
    assert t.save.called


def test_toggle_use_guardrails(widget, mock_templates):
    widget.current_template_index = 0
    widget.toggle_use_guardrails(False)
    t = mock_templates[0]
    assert t.use_guardrails is False
    assert t.save.called


def test_toggle_use_datetime(widget, mock_templates):
    widget.current_template_index = 1
    widget.toggle_use_datetime(False)
    t = mock_templates[1]
    assert t.use_system_datetime_in_system_prompt is False
    assert t.save.called


def test_reset_system_prompt_sets_default(widget, mock_templates):
    widget.current_template_index = 1  # image template
    widget.reset_system_prompt()
    t = mock_templates[1]
    # Should set to AIRUNNER_DEFAULT_IMAGE_SYSTEM_PROMPT
    assert t.system == prompt_templates_widget.AIRUNNER_DEFAULT_IMAGE_SYSTEM_PROMPT
    assert t.save.called
    assert (
        widget.ui.system_prompt.toPlainText()
        == prompt_templates_widget.AIRUNNER_DEFAULT_IMAGE_SYSTEM_PROMPT
    )


def test_reset_guardrails_prompt_sets_default(widget, mock_templates):
    widget.current_template_index = 1  # image template
    widget.reset_guardrails_prompt()
    t = mock_templates[1]
    assert t.guardrails == prompt_templates_widget.AIRUNNER_DEFAULT_IMAGE_LLM_GUARDRAILS
    assert t.save.called
    assert (
        widget.ui.guardrails_prompt.toPlainText()
        == prompt_templates_widget.AIRUNNER_DEFAULT_IMAGE_LLM_GUARDRAILS
    )
