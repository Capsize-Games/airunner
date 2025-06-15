"""
PanelMixin for BrowserWidget.
Handles bookmarks/history panel logic and ItemsWidget signal connections.

Google Python Style Guide applies.
"""

import json
from airunner.components.settings.data.airunner_settings import AIRunnerSettings
from airunner.components.browser.data.settings import (
    BookmarkFolder,
    HistoryEntry,
)
from airunner.components.browser.gui.widgets.items_model import (
    bookmarks_to_model,
    history_to_model,
)


class PanelMixin:
    def _show_panel(self, which: str):
        if which == "bookmarks":
            settings_obj = AIRunnerSettings.objects.filter_by_first(
                name="browser"
            )
            bookmarks = []
            if settings_obj:
                try:
                    data = (
                        settings_obj.data
                        if isinstance(settings_obj.data, dict)
                        else json.loads(settings_obj.data)
                    )
                    bookmarks = data.get("bookmarks", [])
                except Exception as e:
                    self.logger.warning(f"Failed to load bookmarks: {e}")
            model = (
                bookmarks_to_model([BookmarkFolder(**f) for f in bookmarks])
                if bookmarks
                else bookmarks_to_model([])
            )
            self.bookmarks_widget.set_model(model)
            self.history_widget.hide()
            self.bookmarks_widget.show()
            self.ui.left_panel.show()
            self._current_panel = "bookmarks"
            self.ui.left_panel.setWindowTitle("Bookmarks")
            if hasattr(self.bookmarks_widget.ui, "label"):
                self.bookmarks_widget.ui.label.setText("Bookmarks")
            try:
                self.bookmarks_widget.item_activated.disconnect()
            except Exception:
                pass
            self.bookmarks_widget.item_activated.connect(
                self._on_bookmark_activated
            )
            self._connect_items_widget_signals()
        elif which == "history":
            settings_obj = AIRunnerSettings.objects.filter_by_first(
                name="browser"
            )
            history = []
            if settings_obj:
                try:
                    data = (
                        settings_obj.data
                        if isinstance(settings_obj.data, dict)
                        else json.loads(settings_obj.data)
                    )
                    history = [
                        h if isinstance(h, dict) else h.dict()
                        for h in data.get("history", [])
                    ]
                except Exception as e:
                    self.logger.warning(f"Failed to load history: {e}")
            model = (
                history_to_model([HistoryEntry(**h) for h in history])
                if history
                else history_to_model([])
            )
            self.history_widget.set_model(model)
            self.bookmarks_widget.hide()
            self.history_widget.show()
            self.ui.left_panel.show()
            self._current_panel = "history"
            self.ui.left_panel.setWindowTitle("History")
            if hasattr(self.history_widget.ui, "label"):
                self.history_widget.ui.label.setText("History")
            try:
                self.history_widget.item_activated.disconnect()
            except Exception:
                pass
            self.history_widget.item_activated.connect(
                self._on_history_activated
            )
            self._connect_items_widget_signals()
        else:
            self.bookmarks_widget.hide()
            self.history_widget.hide()
            self.ui.left_panel.hide()
            self._current_panel = None
        if which in ("bookmarks", "history"):
            self.ui.splitter.handle(1).setEnabled(True)
            self.ui.splitter.setCollapsible(0, False)
            if self.ui.splitter.sizes()[0] == 0:
                total = self.ui.splitter.size().width() or 800
                left = 250
                center = total - left
                self.ui.splitter.setSizes([left, center, 0])
        else:
            self.ui.splitter.setSizes([0, 1, 0])
            self.ui.splitter.handle(1).setEnabled(False)
            self.ui.splitter.setCollapsible(0, True)
        self._save_splitter_settings()

    def _connect_items_widget_signals(self):
        self.bookmarks_widget.items_deleted.connect(self._on_bookmarks_deleted)
        self.bookmarks_widget.item_edit_requested.connect(
            self._on_bookmark_edit_requested
        )
        self.bookmarks_widget.delete_all_requested.connect(
            self._on_bookmarks_delete_all
        )
        self.bookmarks_widget.sort_requested.connect(
            self._on_bookmarks_sort_requested
        )
        self.history_widget.items_deleted.connect(self._on_history_deleted)
        self.history_widget.item_edit_requested.connect(
            self._on_history_edit_requested
        )
        self.history_widget.delete_all_requested.connect(
            self._on_history_delete_all
        )
        self.history_widget.sort_requested.connect(
            self._on_history_sort_requested
        )

    def _on_bookmark_activated(self, item_data: dict):
        if item_data.get("type") == "bookmark":
            url = item_data.get("url")
            if url:
                self.ui.url.setText(url)
                self.on_submit_button_clicked()

    def _on_history_activated(self, item_data: dict):
        if item_data.get("type") == "history":
            url = item_data.get("url")
            if url:
                self.ui.url.setText(url)
                self.on_submit_button_clicked()
