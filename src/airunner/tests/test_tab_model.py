"""
Tests for the Tab model class.
Follows project pytest and PySide6 GUI test guidelines.
"""

import pytest
from unittest.mock import patch, MagicMock
from PySide6.QtWidgets import QTabWidget, QApplication, QWidget
from airunner.data.models.tab import Tab


@pytest.fixture(scope="module")
def qapp():
    """Fixture to ensure a QApplication exists for widget tests."""
    app = QApplication.instance() or QApplication([])
    yield app


def test_tab_model_attributes():
    """Test Tab model attributes and default values."""
    tab = Tab(section="", name="", active=False, displayed=True, index=0)
    assert tab.section == ""
    assert tab.name == ""
    assert tab.active is False
    assert tab.displayed is True
    assert tab.index == 0


def test_tab_model_creation_with_values():
    """Test Tab model creation with specified values."""
    tab = Tab(
        section="test_section",
        name="Test Tab",
        active=True,
        displayed=False,
        index=3,
    )
    assert tab.section == "test_section"
    assert tab.name == "Test Tab"
    assert tab.active is True
    assert tab.displayed is False
    assert tab.index == 3


@patch("airunner.data.models.tab.session_scope")
def test_update_tabs_sets_active_tab(mock_session_scope, qapp):
    """Test update_tabs method correctly updates active tab state."""
    mock_session = MagicMock()
    mock_query = MagicMock()
    mock_filter = MagicMock()
    mock_update = MagicMock()
    mock_session_context = MagicMock()
    mock_session_context.__enter__.return_value = mock_session
    mock_session_scope.return_value = mock_session_context
    mock_session.query.return_value = mock_query
    mock_query.filter.return_value = mock_filter
    mock_filter.update.return_value = mock_update
    tab_widget = QTabWidget()
    tab_widget.addTab(QWidget(), "Tab 1")
    tab_widget.addTab(QWidget(), "Tab 2")
    tab_widget.addTab(QWidget(), "Tab 3")
    section = "test_section"
    index = 1
    Tab.update_tabs(section, tab_widget, index)
    first_call_args = mock_query.filter.call_args_list[0][0]
    assert len(first_call_args) == 1
    assert first_call_args[0].right.value == section
    first_update_args = mock_filter.update.call_args_list[0][0]
    assert first_update_args[0] == {"active": False}
    second_call_args = mock_query.filter.call_args_list[1][0]
    assert len(second_call_args) == 2
    assert second_call_args[0].right.value == section
    assert second_call_args[1].right.value == "Tab 2"
    second_update_args = mock_filter.update.call_args_list[1][0]
    assert second_update_args[0] == {"active": True}


@patch("airunner.data.models.tab.session_scope")
def test_update_tabs_with_empty_widget(mock_session_scope, qapp):
    """Test update_tabs with an empty QTabWidget."""
    mock_session = MagicMock()
    mock_session_context = MagicMock()
    mock_session_context.__enter__.return_value = mock_session
    mock_session_scope.return_value = mock_session_context
    tab_widget = QTabWidget()
    section = "test_section"
    index = 0
    with pytest.raises(IndexError):
        Tab.update_tabs(section, tab_widget, index)
    mock_session.query.assert_not_called()


@patch("airunner.data.models.tab.session_scope")
def test_update_tabs_with_invalid_index(mock_session_scope, qapp):
    """Test update_tabs with an invalid index."""
    mock_session = MagicMock()
    mock_session_context = MagicMock()
    mock_session_context.__enter__.return_value = mock_session
    mock_session_scope.return_value = mock_session_context
    tab_widget = QTabWidget()
    tab_widget.addTab(QWidget(), "Tab 1")
    tab_widget.addTab(QWidget(), "Tab 2")
    section = "test_section"
    index = 10
    with pytest.raises(IndexError):
        Tab.update_tabs(section, tab_widget, index)
    mock_session.query.assert_not_called()
