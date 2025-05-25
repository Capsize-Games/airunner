"""
Test suite for loading_widget.py in LLM widgets.
"""

import pytest
from airunner.gui.widgets.llm import loading_widget


@pytest.fixture
def loading_widget_instance(qtbot):
    widget = loading_widget.LoadingWidget()
    qtbot.addWidget(widget)
    widget.show()
    return widget


def test_loading_widget_constructs(loading_widget_instance):
    assert loading_widget_instance is not None
