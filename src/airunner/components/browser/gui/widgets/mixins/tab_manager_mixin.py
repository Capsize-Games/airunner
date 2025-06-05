"""
tab_manager_mixin.py

A mixin for QTabWidget-based widgets to provide tab management features:
- Close tab (button, middle-click, Ctrl+W)
- Reopen closed tab (Ctrl+Shift+T)
- New tab (Ctrl+T)
- Save dialog (Ctrl+S)
- Track closed tabs for reopening

Intended for use in both browser and document editor widgets.
"""

from PySide6.QtCore import Qt, QEvent
from PySide6.QtGui import QKeySequence, QShortcut, QMouseEvent


class TabManagerMixin:
    def setup_tab_manager(
        self,
        tab_widget,
        new_tab_callback,
        save_tab_callback,
        reopen_tab_callback=None,
        save_as_tab_callback=None,
    ):
        self._tab_widget = tab_widget
        self._closed_tabs = []
        self._new_tab_callback = new_tab_callback
        self._save_tab_callback = save_tab_callback
        self._reopen_tab_callback = reopen_tab_callback
        self._save_as_tab_callback = save_as_tab_callback

        tab_widget.setTabsClosable(True)
        tab_widget.setMovable(True)
        tab_widget.tabCloseRequested.connect(self._on_tab_close_requested)
        tab_widget.installEventFilter(self)

        # Use ApplicationShortcut context and parent=self (the widget, not the tab widget)
        shortcuts = [
            (QKeySequence("Ctrl+W"), self._close_current_tab),
            (QKeySequence("Ctrl+T"), self._new_tab_callback),
            (QKeySequence("Ctrl+S"), self._save_current_tab),
            (QKeySequence("Ctrl+Shift+T"), self._reopen_last_closed_tab),
            (QKeySequence("Ctrl+Shift+S"), self._save_as_current_tab),
        ]
        for seq, slot in shortcuts:
            sc = QShortcut(seq, self)
            sc.setContext(Qt.ShortcutContext.ApplicationShortcut)
            sc.activated.connect(slot)

    def eventFilter(self, obj, event):
        if (
            obj is self._tab_widget
            and event.type() == QEvent.Type.MouseButtonRelease
        ):
            mouse_event = event  # type: QMouseEvent
            if mouse_event.button() == Qt.MouseButton.MiddleButton:
                tab_index = self._tab_widget.tabBar().tabAt(mouse_event.pos())
                if tab_index != -1:
                    self._on_tab_close_requested(tab_index)
                    return True
        return (
            super().eventFilter(obj, event)
            if hasattr(super(), "eventFilter")
            else False
        )

    def _on_tab_close_requested(self, index):
        widget = self._tab_widget.widget(index)
        if widget:
            file_path = getattr(widget, "file_path", None)
            if file_path:
                self._closed_tabs.append(file_path)
            self._tab_widget.removeTab(index)
            widget.deleteLater()

    def _close_current_tab(self):
        index = self._tab_widget.currentIndex()
        if index != -1:
            self._on_tab_close_requested(index)

    def _reopen_last_closed_tab(self):
        if self._closed_tabs and self._reopen_tab_callback:
            file_path = self._closed_tabs.pop()
            self._reopen_tab_callback(file_path)

    def _save_current_tab(self):
        index = self._tab_widget.currentIndex()
        if index != -1:
            widget = self._tab_widget.widget(index)
            if widget:
                self._save_tab_callback(widget)

    def _save_as_current_tab(self):
        if self._save_as_tab_callback:
            index = self._tab_widget.currentIndex()
            if index != -1:
                widget = self._tab_widget.widget(index)
                if widget:
                    self._save_as_tab_callback(widget)
