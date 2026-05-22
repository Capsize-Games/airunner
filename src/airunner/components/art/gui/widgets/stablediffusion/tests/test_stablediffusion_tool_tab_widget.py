"""Tests for the art-tools tab widget sidebar behavior."""

from types import SimpleNamespace
from unittest.mock import Mock, patch

from airunner.components.application.gui.widgets.base_widget import BaseWidget
from airunner.components.art.gui.widgets.stablediffusion.stablediffusion_tool_tab_widget import (  # noqa: E501
    StablediffusionToolTabWidget,
)


class _FakeSignal:
    def __init__(self) -> None:
        self.callback = None

    def connect(self, callback) -> None:
        self.callback = callback


class _FakeTabBar:
    def __init__(self) -> None:
        self.hide = Mock()


class _FakeTabWidget:
    def __init__(self) -> None:
        self._current_index = 0
        self.currentChanged = _FakeSignal()
        self._tab_bar = _FakeTabBar()

    def tabBar(self):
        return self._tab_bar

    def setCurrentIndex(self, index: int) -> None:
        self._current_index = index

    def currentIndex(self) -> int:
        return self._current_index


def test_configure_tool_tab_widget_hides_tab_bar():
    """The internal tab header should always stay hidden."""
    widget = StablediffusionToolTabWidget.__new__(
        StablediffusionToolTabWidget
    )
    tab_widget = _FakeTabWidget()
    widget.ui = SimpleNamespace(tool_tab_widget_container=tab_widget)

    StablediffusionToolTabWidget._configure_tool_tab_widget(widget)

    tab_widget.tabBar().hide.assert_called_once_with()
    assert (
        tab_widget.currentChanged.callback
        == widget.on_tool_tab_widget_container_currentChanged
    )


def test_show_tool_page_sets_requested_index_and_persists_it():
    """Programmatic page selection should update the nested tab index."""
    widget = StablediffusionToolTabWidget.__new__(
        StablediffusionToolTabWidget
    )
    widget.ui = SimpleNamespace(tool_tab_widget_container=_FakeTabWidget())
    widget.qsettings = Mock()
    widget._requested_active_index = None

    StablediffusionToolTabWidget.show_tool_page(widget, 99)

    assert widget._requested_active_index == 5
    assert widget.ui.tool_tab_widget_container.currentIndex() == 5
    widget.qsettings.setValue.assert_called_once_with(
        "tabs/stablediffusion_tool_tab/active_index",
        5,
    )


def test_show_event_restores_requested_or_saved_index():
    """First show should restore the persisted nested tab selection."""
    widget = StablediffusionToolTabWidget.__new__(
        StablediffusionToolTabWidget
    )
    widget.show_tool_page = Mock()
    widget.qsettings = Mock()
    widget.qsettings.value.return_value = 4
    widget._requested_active_index = None
    event = Mock()

    with patch.object(BaseWidget, "showEvent", autospec=True):
        StablediffusionToolTabWidget.showEvent(widget, event)

    widget.show_tool_page.assert_called_once_with(4)