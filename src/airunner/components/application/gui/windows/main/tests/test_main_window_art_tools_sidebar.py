"""Tests for right-sidebar art tools button routing."""

from types import SimpleNamespace
from unittest.mock import Mock

from airunner.components.application.gui.windows.main.main_window import (
    MainWindow,
)


def _make_button() -> Mock:
    button = Mock()
    button.blockSignals = Mock()
    button.setChecked = Mock()
    return button


def test_toggle_art_tools_tab_selects_requested_page_when_opening():
    """Opening one art-tools button should select its nested tab."""
    window = MainWindow.__new__(MainWindow)
    widget = Mock()
    widget.show_tool_page = Mock()
    window._ensure_art_tools_loaded = Mock(return_value=widget)
    window._toggle_sidebar_page = Mock()

    MainWindow._toggle_art_tools_tab(
        window,
        MainWindow._art_tools_layers_tab_index,
        True,
    )

    widget.show_tool_page.assert_called_once_with(
        MainWindow._art_tools_layers_tab_index
    )
    window._toggle_sidebar_page.assert_called_once_with(
        MainWindow._art_tools_sidebar_index,
        True,
    )


def test_toggle_art_tools_tab_hides_only_when_current_tab_is_active():
    """Turning off the active art-tools button should hide the sidebar."""
    window = MainWindow.__new__(MainWindow)
    window._sidebar_is_visible = Mock(return_value=True)
    window._current_sidebar_index = Mock(
        return_value=MainWindow._art_tools_sidebar_index
    )
    window._current_art_tools_tab_index = Mock(
        return_value=MainWindow._art_tools_grid_tab_index
    )
    window._toggle_sidebar_page = Mock()
    window._sync_sidebar_button_states = Mock()

    MainWindow._toggle_art_tools_tab(
        window,
        MainWindow._art_tools_grid_tab_index,
        False,
    )

    window._toggle_sidebar_page.assert_called_once_with(
        MainWindow._art_tools_sidebar_index,
        False,
    )
    window._sync_sidebar_button_states.assert_not_called()


def test_toggle_art_tools_tab_false_does_not_hide_different_active_tab():
    """Switching buttons should not hide the sidebar from the old button."""
    window = MainWindow.__new__(MainWindow)
    window._sidebar_is_visible = Mock(return_value=True)
    window._current_sidebar_index = Mock(
        return_value=MainWindow._art_tools_sidebar_index
    )
    window._current_art_tools_tab_index = Mock(
        return_value=MainWindow._art_tools_model_tab_index
    )
    window._toggle_sidebar_page = Mock()
    window._sync_sidebar_button_states = Mock()

    MainWindow._toggle_art_tools_tab(
        window,
        MainWindow._art_tools_lora_tab_index,
        False,
    )

    window._toggle_sidebar_page.assert_not_called()
    window._sync_sidebar_button_states.assert_called_once_with()


def test_set_art_tools_buttons_follow_active_nested_tab():
    """Only the button for the visible nested art-tools tab should be checked."""
    window = MainWindow.__new__(MainWindow)
    window.ui = SimpleNamespace(
        art_model_button=_make_button(),
        lora_button=_make_button(),
    )
    window._sidebar_is_visible = Mock(return_value=True)
    window._current_sidebar_index = Mock(
        return_value=MainWindow._art_tools_sidebar_index
    )
    window._current_art_tools_tab_index = Mock(
        return_value=MainWindow._art_tools_lora_tab_index
    )

    MainWindow.set_art_model_button_checked(window)
    MainWindow.set_lora_button_checked(window)

    window.ui.art_model_button.setChecked.assert_called_once_with(False)
    window.ui.lora_button.setChecked.assert_called_once_with(True)
