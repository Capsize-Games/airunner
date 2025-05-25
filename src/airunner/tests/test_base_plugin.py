"""
Tests for the BasePlugin abstract base class.
Follows project pytest and PySide6 GUI test guidelines.
"""

import pytest
from PySide6.QtWidgets import QWidget, QApplication
from airunner.base_plugin import BasePlugin


@pytest.fixture(scope="module")
def qapp():
    """Fixture to ensure a QApplication exists for widget tests."""
    app = QApplication.instance() or QApplication([])
    yield app
    # No explicit teardown needed; handled by global fixture


def test_base_plugin_abstract_methods():
    """Test that BasePlugin enforces implementation of its abstract methods."""
    with pytest.raises(TypeError):
        BasePlugin()


def test_base_plugin_implementation(qapp):
    """Test a concrete implementation of BasePlugin."""

    class TestPlugin(BasePlugin):
        name = "Test Plugin"

        def get_widget(self) -> QWidget:
            return QWidget()

    plugin = TestPlugin()
    assert plugin.name == "Test Plugin"
    widget = plugin.get_widget()
    assert isinstance(widget, QWidget)


def test_base_plugin_multiple_implementations(qapp):
    """Test multiple concrete implementations of BasePlugin with unique widgets."""

    class Plugin1(BasePlugin):
        name = "Plugin 1"

        def get_widget(self) -> QWidget:
            widget = QWidget()
            widget.setObjectName("widget1")
            return widget

    class Plugin2(BasePlugin):
        name = "Plugin 2"

        def get_widget(self) -> QWidget:
            widget = QWidget()
            widget.setObjectName("widget2")
            return widget

    plugin1 = Plugin1()
    plugin2 = Plugin2()
    assert plugin1.name == "Plugin 1"
    assert plugin2.name == "Plugin 2"
    widget1 = plugin1.get_widget()
    widget2 = plugin2.get_widget()
    assert widget1.objectName() == "widget1"
    assert widget2.objectName() == "widget2"
