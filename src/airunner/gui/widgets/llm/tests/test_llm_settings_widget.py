"""
Test suite for llm_settings_widget.py in LLM widgets.
"""

import pytest
from airunner.gui.widgets.llm import llm_settings_widget


@pytest.fixture
def settings_widget(qtbot):
    widget = llm_settings_widget.LLMSettingsWidget()
    qtbot.addWidget(widget)
    widget.show()
    return widget


def test_llm_settings_widget_constructs(settings_widget):
    assert settings_widget is not None


def test_initialize_form_runs(settings_widget):
    settings_widget.initialize_form()
