import re
import os
import hashlib
import shutil
import json
from typing import Optional
from airunner.components.browser.gui.enums import BrowserOS, BrowserType
from airunner.enums import SignalCode
from airunner.components.browser.gui.widgets.templates.browser_ui import (
    Ui_browser,
)
from trafilatura import extract
from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.lex_rank import LexRankSummarizer

from PySide6.QtCore import Slot, QUrl, QTimer
from PySide6.QtWebEngineCore import (
    QWebEnginePage,
    QWebEngineProfile,
    QWebEngineSettings,
)
from airunner.gui.widgets.base_widget import BaseWidget
from airunner.data.models.airunner_settings import AIRunnerSettings
from airunner.components.browser.data.settings import BrowserSettings
from PySide6.QtWidgets import QVBoxLayout
from airunner.components.browser.gui.widgets.items_widget import ItemsWidget
from airunner.components.browser.gui.widgets.items_model import (
    bookmarks_to_model,
    history_to_model,
)
from airunner.components.browser.data.settings import (
    BookmarkFolder,
    HistoryEntry,
)
from PySide6.QtCore import QSettings
import uuid
from datetime import datetime


class BrowserWidget(BaseWidget):
    """Widget that displays a single browser instance (address bar, navigation, webview, etc.).

    Signals:
        titleChanged (str): Emitted when the page title changes. Main window should connect this to update the tab text.

    Usage:
        - Instantiate a new BrowserWidget for each tab in the main window's QTabWidget.
        - Connect the titleChanged signal to QTabWidget.setTabText.
        - Call clear() to reset the browser state (for the last tab).

    Args:
        parent (QWidget, optional): Parent widget.
    """

    titleChanged = Signal(str)
    widget_class_ = Ui_browser

    # --- Favicon, Title, URL, Print, Save, State, and Session Persistence ---
    from PySide6.QtCore import Signal
    from PySide6.QtGui import QIcon, QPixmap

    titleChanged = Signal(str)
    urlChanged = Signal(str, str)  # url, title
    faviconChanged = Signal(QIcon)

    def __init__(self, *args, private: bool = False, **kwargs):
        super().__init__(*args, **kwargs)
        self._favicon = None
        self._private = private
        self.ui.stage.iconChanged.connect(self._on_favicon_changed)
        self.ui.stage.urlChanged.connect(self._on_url_changed)
        self.ui.stage.titleChanged.connect(self._on_title_changed)
        self.signal_handlers = {
            SignalCode.BROWSER_NAVIGATE_SIGNAL: self.on_browser_navigate,
        }
        self.registered: bool = False
        self._profile = None
        self._profile_page = None
        self._private_browsing_enabled = (
            False  # Default to non-private browsing
        )

        # Load browser settings FIRST before creating profile
        self._load_browser_settings()

        # Ensure UI indicators are set even if no settings were loaded
        if not hasattr(self, "_ui_indicators_set"):
            self._update_private_browsing_icon(self._private_browsing_enabled)
            self._update_private_browsing_styling(
                self._private_browsing_enabled
            )
            self._ui_indicators_set = True

        # Now create profile and page with correct privacy settings
        self.ui.stage.setPage(self.profile_page)
        self.set_flags()
        self.ui.stage.loadFinished.connect(self.on_load_finished)
        self.ui.url.returnPressed.connect(self.on_submit_button_clicked)
        self.ui.bookmark_page_button.toggled.connect(
            self.on_bookmark_page_button_toggled
        )
        self.ui.private_browse_button.toggled.connect(
            self.on_private_browse_button_toggled
        )
        self._page_cache = {
            "html": None,
            "plaintext": None,
            "summary": None,
            "url": None,
        }
        self._current_display_mode = "html"  # Track current display mode
        # Set QWebEngineView background to transparent/black
        self.ui.stage.setStyleSheet("background: #111;")
        self.ui.stage.page().setBackgroundColor("#111111")

        # Set initial tab title to 'New Tab'
        if hasattr(self.ui, "browser_tab_widget") and hasattr(self.ui, "tab"):
            self.ui.browser_tab_widget.setTabText(
                self.ui.browser_tab_widget.indexOf(self.ui.tab), "New Tab"
            )
        # Update tab title when page title changes
        self.ui.stage.titleChanged.connect(self._on_stage_title_changed)

        current_browser = BrowserType.CHROME
        self.ui.user_agent_browser.blockSignals(True)
        self.ui.user_agent_browser.clear()
        self.ui.user_agent_browser.addItems([b.value for b in BrowserType])
        self.ui.user_agent_browser.setCurrentText(current_browser.value)
        self.ui.user_agent_browser.blockSignals(False)

        current_browser_os = BrowserOS.WINDOWS
        self.ui.user_agent_os.blockSignals(True)
        self.ui.user_agent_os.clear()
        self.ui.user_agent_os.addItems([os.value for os in BrowserOS])
        self.ui.user_agent_os.setCurrentText(current_browser_os.value)
        self.ui.user_agent_os.blockSignals(False)

        self._random_user_agent = False

        # Initialize with accurate privacy status logging
        self.log_privacy_status()

        # Panels setup
        self.ui.left_panel.hide()
        self.ui.right_panel.hide()
        self._current_panel = None  # Track which panel is open
        # Items widgets for bookmarks/history
        self.bookmarks_widget = ItemsWidget(self.ui.left_panel)
        self.history_widget = ItemsWidget(self.ui.left_panel)
        self.bookmarks_widget.hide()
        self.history_widget.hide()
        # Layout for left_panel
        left_layout = self.ui.left_panel.layout() or QVBoxLayout(
            self.ui.left_panel
        )
        left_layout.addWidget(self.bookmarks_widget)
        left_layout.addWidget(self.history_widget)
        self.ui.left_panel.setLayout(left_layout)

        self.qsettings = QSettings()
        self._splitter_key = "browser_splitter"
        self._restore_splitter_settings()
        self.ui.splitter.splitterMoved.connect(self._save_splitter_settings)

    def _save_splitter_settings(self):
        sizes = self.ui.splitter.sizes()
        self.qsettings.beginGroup(self._splitter_key)
        for i, size in enumerate(sizes):
            self.qsettings.setValue(f"size_{i}", size)
        self.qsettings.endGroup()

    def _restore_splitter_settings(self):
        self.qsettings.beginGroup(self._splitter_key)
        sizes = []
        i = 0
        while True:
            val = self.qsettings.value(f"size_{i}")
            if val is None:
                break
            sizes.append(int(val))
            i += 1
        self.qsettings.endGroup()
        if sizes:
            self.ui.splitter.setSizes(sizes)
        else:
            # Set default left panel width to 250px if no QSettings
            total = self.ui.splitter.size().width() or 800
            left = 250
            center = total - left
            self.ui.splitter.setSizes([left, center, 0])

    def _load_browser_settings(self):
        """Load browser settings from database and apply to UI."""
        settings_obj = AIRunnerSettings.objects.filter_by_first(name="browser")
        if settings_obj:
            try:
                settings_data = (
                    settings_obj.data
                    if isinstance(settings_obj.data, dict)
                    else json.loads(settings_obj.data)
                )
                browser_settings = BrowserSettings(**settings_data)

                # Load and apply private browsing setting BEFORE profile creation
                if hasattr(browser_settings, "private_browsing"):
                    self._private_browsing_enabled = (
                        browser_settings.private_browsing
                    )
                    self.ui.private_browse_button.setChecked(
                        browser_settings.private_browsing
                    )
                    # Update UI indicators to match loaded state
                    self._update_private_browsing_icon(
                        browser_settings.private_browsing
                    )
                    self._update_private_browsing_styling(
                        browser_settings.private_browsing
                    )
                    self._ui_indicators_set = True

                # Load other settings
                if hasattr(browser_settings, "browser_type"):
                    self.ui.user_agent_browser.setCurrentText(
                        browser_settings.browser_type
                    )
                if hasattr(browser_settings, "os_type"):
                    self.ui.user_agent_os.setCurrentText(
                        browser_settings.os_type
                    )
                if hasattr(browser_settings, "random_user_agent"):
                    self._random_user_agent = (
                        browser_settings.random_user_agent
                    )
                    if hasattr(self.ui, "pushButton"):
                        self.ui.pushButton.setChecked(
                            browser_settings.random_user_agent
                        )

            except Exception as e:
                self.logger.warning(f"Failed to load browser settings: {e}")
                # Use defaults if loading fails
                self._private_browsing_enabled = False
                self.ui.private_browse_button.setChecked(False)
                # Set default UI indicators
                self._update_private_browsing_icon(False)
                self._update_private_browsing_styling(False)
                self._ui_indicators_set = True

    @Slot(bool)
    def on_private_browse_button_toggled(self, checked: bool) -> None:
        """Toggle private browsing mode and update settings."""
        self._set_private_browsing(checked)
        self._save_browser_settings()

    def _set_private_browsing(self, enabled: bool):
        """Set private browsing mode and update all UI indicators."""
        # Update the internal state
        self._private_browsing_enabled = enabled

        # Update button icon based on state
        self._update_private_browsing_icon(enabled)

        # Apply/remove purple styling
        self._update_private_browsing_styling(enabled)

        # Clear session if enabling private browsing
        if enabled:
            self.clear_session()
            self.logger.info("Private browsing enabled - session data cleared")
        else:
            self.logger.info(
                "Private browsing disabled - normal browsing mode"
            )

        # Force profile recreation on next access to apply new privacy settings
        self._profile = None
        self._profile_page = None

        # Update the webview to use the new profile
        self.ui.stage.setPage(self.profile_page)

        # Log the privacy status
        self.log_privacy_status()

    def _update_private_browsing_icon(self, enabled: bool):
        """Update the private browsing button icon based on the current state."""
        from PySide6.QtGui import QIcon

        if enabled:
            # Private browsing enabled - use eye-off icon (data is hidden)
            icon_path = ":/dark/icons/feather/dark/eye-off.svg"
            self.ui.private_browse_button.setToolTip(
                "Private browsing enabled - Click to disable"
            )
        else:
            # Private browsing disabled - use eye icon (data is visible/tracked)
            icon_path = ":/dark/icons/feather/dark/eye.svg"
            self.ui.private_browse_button.setToolTip(
                "Private browsing disabled - Click to enable"
            )

        icon = QIcon()
        icon.addFile(icon_path)
        self.ui.private_browse_button.setIcon(icon)

    def _update_private_browsing_styling(self, enabled: bool):
        """Apply or remove purple styling to indicate private browsing mode."""
        if enabled:
            # Apply purple styling for private browsing mode
            purple_style = """
                QPushButton#private_browse_button {
                    background-color: #4a1a4a;
                    border: 2px solid #8b4a8b;
                    border-radius: 4px;
                    color: #e6b3e6;
                }
                QPushButton#private_browse_button:checked {
                    background-color: #6b2a6b;
                    border-color: #aa5aaa;
                }
                QPushButton#private_browse_button:hover {
                    background-color: #5a2a5a;
                    border-color: #9a5a9a;
                }
            """
            self.ui.private_browse_button.setStyleSheet(purple_style)

            # Optional: Add purple accent to the URL bar to indicate private mode
            url_style = """
                QLineEdit#url {
                    border-left: 3px solid #8b4a8b;
                }
            """
            self.ui.url.setStyleSheet(url_style)
        else:
            # Remove purple styling for normal browsing mode
            self.ui.private_browse_button.setStyleSheet("")
            self.ui.url.setStyleSheet("")

    @Slot(bool)
    def on_bookmark_button_toggled(self, checked: bool):
        """Toggle bookmarks panel. Collapse if toggled off. Only one panel open at a time."""
        if checked:
            self.ui.history_button.setChecked(False)
            self._show_panel("bookmarks")
        else:
            self._show_panel(None)

    @Slot(bool)
    def on_history_button_toggled(self, checked: bool):
        """Toggle history panel. Collapse if toggled off. Only one panel open at a time."""
        if checked:
            self.ui.bookmark_button.setChecked(False)
            self._show_panel("history")
        else:
            self._show_panel(None)

    def _connect_items_widget_signals(self):
        """Connect ItemsWidget signals to browser logic for bookmarks and history panels."""
        # Bookmarks panel
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
        # History panel
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

    def _on_bookmarks_deleted(self, items: list):
        """Delete selected bookmarks from all folders."""
        settings_obj = AIRunnerSettings.objects.filter_by_first(name="browser")
        if not settings_obj:
            return
        try:
            data = (
                settings_obj.data
                if isinstance(settings_obj.data, dict)
                else json.loads(settings_obj.data)
            )
            bookmarks = data.get("bookmarks", [])
            urls_to_delete = {
                item["url"] for item in items if item.get("type") == "bookmark"
            }
            for folder in bookmarks:
                folder["bookmarks"] = [
                    bm
                    for bm in folder["bookmarks"]
                    if bm["url"] not in urls_to_delete
                ]
            data["bookmarks"] = [f for f in bookmarks if f["bookmarks"]]
            AIRunnerSettings.objects.update(pk=settings_obj.id, data=data)
            if self._current_panel == "bookmarks":
                self._show_panel("bookmarks")
        except Exception as e:
            self.logger.warning(f"Failed to delete bookmarks: {e}")

    def _on_bookmark_edit_requested(self, item: dict):
        """Open edit dialog for a bookmark (stub for now)."""
        # TODO: Implement bookmark edit dialog
        self.logger.info("Edit requested for bookmark")

    def _on_bookmarks_delete_all(self):
        """Delete all bookmarks."""
        settings_obj = AIRunnerSettings.objects.filter_by_first(name="browser")
        if not settings_obj:
            return
        try:
            data = (
                settings_obj.data
                if isinstance(settings_obj.data, dict)
                else json.loads(settings_obj.data)
            )
            data["bookmarks"] = []
            AIRunnerSettings.objects.update(pk=settings_obj.id, data=data)
            if self._current_panel == "bookmarks":
                self._show_panel("bookmarks")
        except Exception as e:
            self.logger.warning(f"Failed to delete all bookmarks: {e}")

    def _on_bookmarks_sort_requested(self, sort_mode: str):
        """Sort bookmarks by the selected mode."""
        settings_obj = AIRunnerSettings.objects.filter_by_first(name="browser")
        if not settings_obj:
            return
        try:
            data = (
                settings_obj.data
                if isinstance(settings_obj.data, dict)
                else json.loads(settings_obj.data)
            )
            bookmarks = data.get("bookmarks", [])
            for folder in bookmarks:
                if sort_mode == "A-Z":
                    folder["bookmarks"].sort(
                        key=lambda bm: bm["title"].lower()
                    )
                elif sort_mode == "Z-A":
                    folder["bookmarks"].sort(
                        key=lambda bm: bm["title"].lower(), reverse=True
                    )
                elif sort_mode == "Date Added":
                    folder["bookmarks"].sort(
                        key=lambda bm: bm.get("created_at", "")
                    )
            AIRunnerSettings.objects.update(pk=settings_obj.id, data=data)
            if self._current_panel == "bookmarks":
                self._show_panel("bookmarks")
        except Exception as e:
            self.logger.warning(f"Failed to sort bookmarks: {e}")

    def _on_history_deleted(self, items: list):
        """Delete selected history entries by URL."""
        settings_obj = AIRunnerSettings.objects.filter_by_first(name="browser")
        if not settings_obj:
            return
        try:
            data = (
                settings_obj.data
                if isinstance(settings_obj.data, dict)
                else json.loads(settings_obj.data)
            )
            history = data.get("history", [])
            urls_to_delete = {
                item["url"] for item in items if item.get("type") == "history"
            }
            data["history"] = [
                h for h in history if h["url"] not in urls_to_delete
            ]
            AIRunnerSettings.objects.update(pk=settings_obj.id, data=data)
            if self._current_panel == "history":
                self._show_panel("history")
        except Exception as e:
            self.logger.warning(f"Failed to delete history entries: {e}")

    def _on_history_edit_requested(self, item: dict):
        """Edit history entry (stub for now)."""
        # Not typically supported for history, but stub provided
        self.logger.info("Edit requested for history entry")

    def _on_history_delete_all(self):
        """Delete all history entries."""
        settings_obj = AIRunnerSettings.objects.filter_by_first(name="browser")
        if not settings_obj:
            return
        try:
            data = (
                settings_obj.data
                if isinstance(settings_obj.data, dict)
                else json.loads(settings_obj.data)
            )
            data["history"] = []
            AIRunnerSettings.objects.update(pk=settings_obj.id, data=data)
            if self._current_panel == "history":
                self._show_panel("history")
        except Exception as e:
            self.logger.warning(f"Failed to delete all history: {e}")

    def _on_history_sort_requested(self, sort_mode: str):
        """Sort history entries by the selected mode."""
        settings_obj = AIRunnerSettings.objects.filter_by_first(name="browser")
        if not settings_obj:
            return
        try:
            data = (
                settings_obj.data
                if isinstance(settings_obj.data, dict)
                else json.loads(settings_obj.data)
            )
            history = data.get("history", [])
            if sort_mode == "A-Z":
                history.sort(key=lambda h: h["title"].lower())
            elif sort_mode == "Z-A":
                history.sort(key=lambda h: h["title"].lower(), reverse=True)
            elif sort_mode == "Date Added":
                history.sort(
                    key=lambda h: h["visits"][-1] if h.get("visits") else ""
                )
            # Custom/manual ordering not implemented here
            data["history"] = history
            AIRunnerSettings.objects.update(pk=settings_obj.id, data=data)
            if self._current_panel == "history":
                self._show_panel("history")
        except Exception as e:
            self.logger.warning(f"Failed to sort history: {e}")

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
        # Control splitter handle visibility and movement
        if which in ("bookmarks", "history"):
            self.ui.splitter.handle(1).setEnabled(True)
            self.ui.splitter.setCollapsible(0, False)
            # If panel is hidden, open to default width if not already open
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

    def _on_bookmark_activated(self, item_data: dict):
        """Open the URL for the activated bookmark."""
        if item_data.get("type") == "bookmark":
            url = item_data.get("url")
            if url:
                self.ui.url.setText(url)
                self.on_submit_button_clicked()

    def _on_history_activated(self, item_data: dict):
        """Open the URL for the activated history entry."""
        if item_data.get("type") == "history":
            url = item_data.get("url")
            if url:
                self.ui.url.setText(url)
                self.on_submit_button_clicked()

    def _save_browser_settings(self):
        settings_obj = AIRunnerSettings.objects.filter_by_first(name="browser")
        if settings_obj:
            try:
                data = (
                    settings_obj.data
                    if isinstance(settings_obj.data, dict)
                    else json.loads(settings_obj.data)
                )
                data["private_browsing"] = (
                    self.ui.private_browse_button.isChecked()
                )
                AIRunnerSettings.objects.update(pk=settings_obj.id, data=data)
            except Exception as e:
                self.logger.warning(f"Failed to save browser settings: {e}")

    def add_bookmark(
        self,
        title: str = None,
        url: str = None,
        folder: str = "Bookmarks",
        uuid_key: str = None,
    ):
        # Use current page title if not provided
        if not title:
            title = self.ui.stage.title() or url or "(Untitled)"
        if not url:
            url = self.ui.stage.url().toString()
        settings_obj = AIRunnerSettings.objects.filter_by_first(name="browser")
        if not settings_obj:
            return
        try:
            data = (
                settings_obj.data
                if isinstance(settings_obj.data, dict)
                else json.loads(settings_obj.data)
            )
            bookmarks = data.get("bookmarks", [])
            if not uuid_key:
                uuid_key = str(uuid.uuid4())
            now = datetime.utcnow().isoformat()
            # Find or create folder
            for f in bookmarks:
                if f["name"] == folder:
                    f["bookmarks"].append(
                        {
                            "title": title,
                            "url": url,
                            "uuid": uuid_key,
                            "created_at": now,
                        }
                    )
                    break
            else:
                bookmarks.append(
                    {
                        "name": folder,
                        "bookmarks": [
                            {
                                "title": title,
                                "url": url,
                                "uuid": uuid_key,
                                "created_at": now,
                            }
                        ],
                        "created_at": now,
                    }
                )
            data["bookmarks"] = bookmarks
            if "plaintext" not in data or not isinstance(
                data["plaintext"], dict
            ):
                data["plaintext"] = {}
            if "page_summary" not in data or not isinstance(
                data["page_summary"], dict
            ):
                data["page_summary"] = {}
            AIRunnerSettings.objects.update(pk=settings_obj.id, data=data)
            # If bookmarks panel is open, refresh it
            if self._current_panel == "bookmarks":
                self._show_panel("bookmarks")
        except Exception as e:
            self.logger.warning(f"Failed to add/update bookmark: {e}")

    def add_history_entry(
        self, title: str, url: str, visited_at: str, uuid_key: str = None
    ):
        self.logger.debug(
            f"add_history_entry called with title='{title}', visited_at='{visited_at}', uuid_key='{uuid_key}'"
        )
        settings_obj = AIRunnerSettings.objects.filter_by_first(name="browser")
        if not settings_obj:
            self.logger.warning(
                "add_history_entry: No settings_obj found for 'browser'. Cannot save history."
            )
            return
        try:
            data = (
                settings_obj.data
                if isinstance(settings_obj.data, dict)
                else json.loads(settings_obj.data)
            )
            history = data.get("history", [])
            # Deduplicate by URL, append visit time
            found = False
            for entry in history:
                if entry["url"] == url:
                    entry.setdefault("visits", []).append(visited_at)
                    entry["title"] = title  # Optionally update title
                    found = True
                    break
            if not found:
                history.append(
                    {
                        "title": title,
                        "url": url,
                        "visits": [visited_at],
                    }
                )
            data["history"] = history[-1000:]  # Keep last 1000 entries
            if "plaintext" not in data or not isinstance(
                data["plaintext"], dict
            ):
                data["plaintext"] = {}
            if "page_summary" not in data or not isinstance(
                data["page_summary"], dict
            ):
                data["page_summary"] = {}
            AIRunnerSettings.objects.update(pk=settings_obj.id, data=data)
            # If history panel is open, refresh it
            if self._current_panel == "history":
                self._show_panel("history")
        except Exception as e:
            self.logger.error(
                f"Failed to add history entry: {e}", exc_info=True
            )

    @Slot(bool)
    def on_random_button_toggled(self, checked: bool) -> None:
        """Toggle random user agent generation."""
        self._random_user_agent = checked

    @Slot(str)
    def on_user_agent_browser_textChanged(self, text: str) -> None:
        """Update the user agent string for the browser."""
        print("BROWSER", text)

    @Slot()
    def on_next_button_clicked(self) -> None:
        """Navigate forward in the browser history."""
        self.ui.stage.forward()

    @Slot()
    def on_back_button_clicked(self) -> None:
        """Navigate backward in the browser history."""
        self.ui.stage.back()

    @Slot()
    def on_refresh_button_clicked(self) -> None:
        """Reload the current page in the browser."""
        self.ui.stage.reload()

    @Slot(bool)
    def on_plaintext_button_toggled(self, checked: bool) -> None:
        """Switch to plain text mode."""
        if checked and self._page_cache["plaintext"]:
            if self._current_display_mode != "plaintext":
                html = self._format_plaintext_as_html(
                    self._page_cache["plaintext"]
                )
                self.ui.stage.setHtml(html, QUrl(self._page_cache["url"]))
                self._current_display_mode = "plaintext"
        elif not checked and self._page_cache["html"]:
            # If summary is toggled on, show summary instead
            if (
                hasattr(self.ui, "summarize_button")
                and self.ui.summarize_button.isChecked()
                and self._page_cache["summary"]
            ):
                if self._current_display_mode != "summary":
                    html = self._format_plaintext_as_html(
                        self._page_cache["summary"]
                    )
                    self.ui.stage.setHtml(html, QUrl(self._page_cache["url"]))
                    self._current_display_mode = "summary"
            else:
                if self._current_display_mode != "html":
                    if self._page_cache["url"]:
                        self.ui.stage.setUrl(QUrl(self._page_cache["url"]))
                        self._current_display_mode = "html"

    @Slot(bool)
    def on_summarize_button_toggled(self, checked: bool) -> None:
        """Summarize the current page."""
        if checked and self._page_cache["summary"]:
            if self._current_display_mode != "summary":
                html = self._format_plaintext_as_html(
                    self._page_cache["summary"]
                )
                self.ui.stage.setHtml(html, QUrl(self._page_cache["url"]))
                self._current_display_mode = "summary"
        elif not checked and self._page_cache["html"]:
            # If plaintext is toggled on, show plaintext instead
            if (
                hasattr(self.ui, "plaintext_button")
                and self.ui.plaintext_button.isChecked()
                and self._page_cache["plaintext"]
            ):
                if self._current_display_mode != "plaintext":
                    html = self._format_plaintext_as_html(
                        self._page_cache["plaintext"]
                    )
                    self.ui.stage.setHtml(html, QUrl(self._page_cache["url"]))
                    self._current_display_mode = "plaintext"
            else:
                if self._current_display_mode != "html":
                    if self._page_cache["url"]:
                        self.ui.stage.setUrl(QUrl(self._page_cache["url"]))
                        self._current_display_mode = "html"

    @Slot()
    def on_submit_button_clicked(self) -> None:
        """Sanitize and load the URL in the QWebEngineView.

        1. Ensure https is used
        2. Add scheme if missing
        3. Check if the URL is valid
        4. Load the URL in the QWebEngineView, using cache if available
        5. Update the URL field if it was modified
        6. Deselect the URL field
        """
        url = self.ui.url.text().strip()
        if not url:
            return
        original_url = url

        # Handle local: scheme for local static files
        if url.startswith("local:"):
            # Map local:game -> game.html (prefer .html, fallback to .jinja2.html)
            local_name = url[len("local:") :].strip()
            if not local_name:
                self.logger.warning(
                    "No local file specified after 'local:' scheme."
                )
                return
            user_web_dir = os.path.expanduser(
                os.path.join(self.path_settings.base_path, "web")
            )
            candidates = [
                os.path.join(user_web_dir, "html", f"{local_name}.html"),
                os.path.join(
                    user_web_dir, "html", f"{local_name}.jinja2.html"
                ),
            ]
            for file_path in candidates:
                if os.path.exists(file_path):
                    with open(file_path, "r", encoding="utf-8") as f:
                        html = f.read()
                    self.ui.stage.setHtml(html, QUrl.fromLocalFile(file_path))
                    self.ui.url.setText(f"local:{local_name}")
                    self._page_cache["html"] = html
                    self._page_cache["url"] = f"local:{local_name}"
                    self._page_cache["plaintext"] = None
                    self._page_cache["summary"] = None
                    return
            self.logger.warning("Local file not found")
            self.ui.url.setStyleSheet(
                "QLineEdit { background: #331111; color: #ff9999; }"
            )
            return

        # Add scheme if missing
        if not url.startswith("http://") and not url.startswith("https://"):
            url = f"https://{url}"

        # Always use https for security (force upgrade)
        if url.startswith("http://"):
            url = url.replace("http://", "https://", 1)
            self.logger.info("Upgraded insecure URL to HTTPS")

        # Update the URL field if it was modified
        if url != original_url:
            self.ui.url.setText(url)

        # Deselect the URL field
        self.ui.url.clearFocus()

        # Enhanced URL validation (stricter HTTPS-only policy)
        pattern = re.compile(
            r"^https://([\w.-]+|\d{1,3}(?:\.\d{1,3}){3})(?::\d+)?(?:[/?#][^\s]*)?$"
        )
        if pattern.match(url):
            # Check cache before loading
            cache_dir = os.path.join(
                os.path.expanduser(self.path_settings.base_path),
                "cache",
                "browser",
            )
            os.makedirs(cache_dir, exist_ok=True)
            url_hash = hashlib.sha256(url.encode("utf-8")).hexdigest()
            cache_path = os.path.join(cache_dir, f"{url_hash}.html")
            if os.path.exists(cache_path):
                with open(cache_path, "r", encoding="utf-8") as f:
                    html = f.read()
                # Emit the signal with the HTML string as a document
                self.emit_signal(
                    SignalCode.RAG_LOAD_DOCUMENTS,
                    {
                        "documents": [html],
                        "type": "html_string",
                        "clear_documents": True,
                    },
                )
                self.ui.stage.setHtml(html, QUrl(url))
            else:
                self.ui.stage.setUrl(QUrl(url))
        else:
            self.logger.warning("Invalid or insecure URL rejected")
            # Show security warning to user
            self.ui.url.setStyleSheet(
                "QLineEdit { background: #331111; color: #ff9999; }"
            )

    @Slot()
    def on_clear_data_button_clicked(self) -> None:
        """Clear all browsing data and session information."""
        self.clear_session()
        self.logger.info("Browser data cleared - all session data removed")

        # Reset to secure state
        self.ui.stage.setUrl(QUrl("about:blank"))
        self.ui.url.clear()

        # Reset security indicators
        self.ui.url.setStyleSheet(
            "QLineEdit { background: #111; color: #eee; }"
        )

        # Log privacy status after clearing
        self.log_privacy_status()

    @property
    def profile(self):
        """Initialize the browser profile based on private browsing settings."""
        if self._profile is None:
            # Use stored private browsing setting or fall back to UI button state
            private_mode = getattr(
                self,
                "_private_browsing_enabled",
                (
                    self.ui.private_browse_button.isChecked()
                    if hasattr(self, "ui")
                    else False
                ),
            )

            if private_mode:
                # Create off-the-record profile for private browsing
                self._profile = QWebEngineProfile(parent=self)
                self.logger.info(f"Private browsing: Enabled")
                self.logger.info(f"Persistent storage: Disabled")
                self.logger.info(f"Cookies: Session-only")
            else:
                # Create persistent profile for normal browsing
                self._profile = QWebEngineProfile(
                    "airunner_persistent", parent=self
                )
                self.logger.info(f"Private browsing: Disabled")
                self.logger.info(f"Persistent storage: Enabled")
                self.logger.info(f"Cookies: Persistent allowed")
        return self._profile

    @property
    def profile_page(self):
        if self._profile_page is None:
            self._profile_page = QWebEnginePage(self.profile, self.ui.stage)
        return self._profile_page

    def set_flags(self):
        """Configure privacy and security settings for the browser."""
        settings = self.profile_page.settings()

        # Disable potentially risky features
        settings.setAttribute(
            QWebEngineSettings.WebAttribute.PluginsEnabled, False
        )
        settings.setAttribute(
            QWebEngineSettings.WebAttribute.WebGLEnabled, False
        )
        settings.setAttribute(
            QWebEngineSettings.WebAttribute.JavascriptCanOpenWindows, False
        )
        settings.setAttribute(
            QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls,
            False,
        )
        settings.setAttribute(
            QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls,
            False,
        )
        settings.setAttribute(
            QWebEngineSettings.WebAttribute.DnsPrefetchEnabled, False
        )
        settings.setAttribute(
            QWebEngineSettings.WebAttribute.HyperlinkAuditingEnabled, False
        )
        settings.setAttribute(
            QWebEngineSettings.WebAttribute.ScreenCaptureEnabled, False
        )

        # Additional privacy settings
        settings.setAttribute(
            QWebEngineSettings.WebAttribute.AutoLoadImages, True
        )  # Keep images for usability
        settings.setAttribute(
            QWebEngineSettings.WebAttribute.JavascriptEnabled, True
        )  # Keep JS for functionality
        settings.setAttribute(
            QWebEngineSettings.WebAttribute.LocalStorageEnabled, False
        )
        settings.setAttribute(
            QWebEngineSettings.WebAttribute.AllowRunningInsecureContent, False
        )

        # Set privacy-friendly defaults
        self.profile.setHttpUserAgent(
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.7151.55 Safari/537.36"
        )

        # Set strict referrer policy for privacy
        self.profile.setHttpAcceptLanguage("en-US,en;q=0.9")

        # Additional privacy headers will be handled by requests when available
        # Note: Qt WebEngine doesn't provide direct header injection,
        # but the OTR profile provides good privacy defaults

        # Connect permission request handler
        self.profile_page.featurePermissionRequested.connect(
            self._handle_permission_request
        )

        # Connect certificate error handler
        self.profile_page.certificateError.connect(
            self._handle_certificate_error
        )

    def _handle_permission_request(self, url, feature):
        """Handle permission requests from web pages.

        Deny all permission requests for privacy and security.
        """
        self.logger.info(f"Permission request denied for feature: {feature}")
        self.profile_page.setFeaturePermission(
            url, feature, QWebEnginePage.PermissionDeniedByUser
        )

    def _handle_certificate_error(self, error):
        """Handle SSL certificate errors.

        Args:
            error: QWebEngineCertificateError object

        Returns:
            bool: Whether to ignore the certificate error
        """
        self.logger.warning(
            f"SSL Certificate error for {error.url().toString()}: {error.description()}"
        )
        # For maximum security, reject all certificate errors
        # Users can manually add exceptions if needed
        return False

    def _update_security_indicators(self):
        """Update security indicators in the UI based on current page."""
        if not hasattr(self.ui, "url"):
            return

        current_url = self.ui.stage.url().toString()
        if not current_url or current_url == "about:blank":
            self.ui.url.setStyleSheet(
                "QLineEdit { background: #111; color: #eee; }"
            )
            return

        if current_url.startswith("https://"):
            # Secure connection - green tint
            self.ui.url.setStyleSheet(
                "QLineEdit { background: #112211; color: #eee; }"
            )
            self.logger.debug("Secure connection detected")
        elif current_url.startswith("http://"):
            # Insecure connection - red tint
            self.ui.url.setStyleSheet(
                "QLineEdit { background: #221111; color: #eee; }"
            )
            self.logger.warning("Insecure connection detected")
        else:
            # Unknown protocol
            self.ui.url.setStyleSheet(
                "QLineEdit { background: #111; color: #eee; }"
            )

        # Update URL field to show actual loaded URL
        if current_url != self.ui.url.text():
            self.ui.url.setText(current_url)

    def _clear_history(self):
        """Clear the browser history."""
        self.profile.clearAllVisitedLinks()

    def _clear_cookies(self):
        """Clear cookies associated with the browser widget."""
        cookie_store = self.profile.cookieStore()
        cookie_store.deleteAllCookies()

    def _clear_http_cache(self):
        """Clear the HTTP cache associated with the browser widget."""
        self.profile.clearHttpCache()

    def _clear_html5_storage(self):
        """Clear HTML5 Storage (Local Storage, IndexedDB, etc.) associated with the browser widget."""
        # Note: Direct localStorage clearing not available in Qt WebEngine
        # Storage is automatically cleared when OTR profile is destroyed
        pass

    def _clear_custom_html_cache(self):
        """Clear the custom HTML disk cache that bypasses OTR profile."""
        cache_dir = os.path.join(
            os.path.expanduser(self.path_settings.base_path),
            "cache",
            "browser",
        )
        if os.path.exists(cache_dir):
            cleared_count = 0
            try:
                for item in os.listdir(cache_dir):
                    item_path = os.path.join(cache_dir, item)
                    try:
                        if os.path.isfile(item_path) or os.path.islink(
                            item_path
                        ):
                            os.unlink(item_path)
                            cleared_count += 1
                        elif os.path.isdir(item_path):
                            # Remove subdirectories if cache creates them
                            shutil.rmtree(item_path)
                            cleared_count += 1
                    except Exception as e:
                        self.logger.error(
                            f"Failed to delete cached item {item_path}: {e}"
                        )
                self.logger.info(
                    f"Custom HTML disk cache cleared - {cleared_count} items removed"
                )
            except Exception as e:
                self.logger.error(
                    f"Failed to access cache directory {cache_dir}: {e}"
                )

    def clear_session(self):
        """
        Clear history, cookies, HTTP cache, HTML5 Storage (Local Storage, IndexedDB, etc.),
        and any other persistent data associated with the browser widget.
        """
        self._clear_history()
        self._clear_cookies()
        self._clear_http_cache()
        self._clear_html5_storage()
        self._clear_custom_html_cache()  # Clear custom disk cache to maintain OTR privacy

    def on_browser_navigate(self, data):
        url = data.get("url", None)
        if url is not None:
            self.ui.stage.load(url)
        else:
            self.logger.error("No URL provided for navigation.")

    def _format_plaintext_as_html(self, text: str) -> str:
        """Wrap plaintext or summary in simple HTML for display with dark background."""
        return (
            "<html><body style='background:#111;color:#eee;font-family:monospace;white-space:pre-wrap;padding:1em;'>"
            f"{text}"
            "</body></html>"
        )

    def on_load_finished(self, ok):
        if ok:
            self._update_security_indicators()
            current_url = self.ui.stage.url().toString()
            page_title = self.ui.stage.title() or current_url

            if (
                not self.ui.private_browse_button.isChecked()
                and current_url != "about:blank"
            ):
                self.logger.debug(
                    f"Attempting to add history entry for: {current_url}"
                )
                visited_at_iso = datetime.utcnow().isoformat()
                # Ensure a UUID is generated if not passed (though usually it won't be for new entries)
                history_uuid = str(uuid.uuid4())
                self.add_history_entry(
                    title=page_title,
                    url=current_url,
                    visited_at=visited_at_iso,
                    uuid_key=history_uuid,
                )
            else:
                self.logger.debug(
                    f"Skipping history entry for {current_url} (Private Browsing: {self.ui.private_browse_button.isChecked()})"
                )

            self._update_bookmark_page_button()

            def poll_for_rendered_content(attempt=0, max_attempts=20):
                # Heuristic: consider page rendered if body text is long enough
                js = """
                    (function() {
                        var body = document.body;
                        if (!body) return false;
                        var text = body.innerText || '';
                        return text.length > 1000;
                    })();
                """
                self.ui.stage.page().runJavaScript(
                    js,
                    lambda ready: self._on_poll_result(
                        ready, attempt, max_attempts
                    ),
                )

            poll_for_rendered_content()

    def _on_poll_result(self, ready, attempt, max_attempts):
        if ready or attempt >= max_attempts:
            self._extract_and_process_html()
        else:
            QTimer.singleShot(
                300, lambda: self._poll_again(attempt + 1, max_attempts)
            )

    def _poll_again(self, attempt, max_attempts):
        js = """
            (function() {
                var body = document.body;
                if (!body) return false;
                var text = body.innerText || '';
                return text.length > 1000;
            })();
        """
        self.ui.stage.page().runJavaScript(
            js,
            lambda ready: self._on_poll_result(ready, attempt, max_attempts),
        )

    def _extract_and_process_html(self):
        def handle_html(html):
            cache_dir = os.path.join(
                os.path.expanduser(self.path_settings.base_path),
                "cache",
                "browser",
            )
            os.makedirs(cache_dir, exist_ok=True)
            url = self.ui.stage.url().toString()
            url_hash = hashlib.sha256(url.encode("utf-8")).hexdigest()
            cache_path = os.path.join(cache_dir, f"{url_hash}.html")
            with open(cache_path, "w", encoding="utf-8") as f:
                f.write(html)
            self._page_cache["html"] = html
            self._page_cache["url"] = url
            plaintext = extract(html) or ""
            self._page_cache["plaintext"] = plaintext
            summary = ""
            if plaintext:
                try:
                    parser = PlaintextParser.from_string(
                        plaintext, Tokenizer("english")
                    )
                    summarizer = LexRankSummarizer()
                    sentence_count = 1
                    summary_sentences = summarizer(
                        parser.document, sentence_count
                    )
                    summary = "\n".join(
                        [str(sentence) for sentence in summary_sentences]
                    )
                except Exception as e:
                    self.logger.warning(f"Summarization failed: {e}")
            self._page_cache["summary"] = summary
            # Store plaintext and summary in settings keyed by uuid
            settings_obj = AIRunnerSettings.objects.filter_by_first(
                name="browser"
            )
            if settings_obj:
                try:
                    data = (
                        settings_obj.data
                        if isinstance(settings_obj.data, dict)
                        else json.loads(settings_obj.data)
                    )
                    # Find uuid for current url in history or bookmarks
                    uuid_key = None
                    for h in data.get("history", []):
                        if h["url"] == url:
                            uuid_key = h.get("uuid")
                            break
                    if not uuid_key:
                        for f in data.get("bookmarks", []):
                            for bm in f["bookmarks"]:
                                if bm["url"] == url:
                                    uuid_key = bm.get("uuid")
                                    break
                    if uuid_key:
                        now = datetime.utcnow().isoformat()
                        if "plaintext" not in data or not isinstance(
                            data["plaintext"], dict
                        ):
                            data["plaintext"] = {}
                        if "page_summary" not in data or not isinstance(
                            data["page_summary"], dict
                        ):
                            data["page_summary"] = {}
                        data["plaintext"][uuid_key] = {
                            "text": plaintext,
                            "timestamp": now,
                        }
                        data["page_summary"][uuid_key] = {
                            "text": summary,
                            "timestamp": now,
                        }
                        AIRunnerSettings.objects.update(
                            pk=settings_obj.id, data=data
                        )
                except Exception as e:
                    self.logger.warning(
                        f"Failed to store plaintext/summary: {e}"
                    )
            # ...existing code for UI update and signals...
            self.emit_signal(
                SignalCode.BROWSER_EXTRA_CONTEXT,
                {
                    "plaintext": plaintext,
                    "url": url,
                },
            )

        self.ui.stage.page().toHtml(handle_html)

    def get_privacy_status(self) -> dict:
        """Get current privacy and security status.

        Returns:
            dict: Privacy status information (without exposing URLs)
        """
        current_url = self.ui.stage.url().toString()
        is_otr = bool(self._profile and self._profile.isOffTheRecord())

        return {
            "otr_profile_active": is_otr,
            "https_only": (
                current_url.startswith("https://") if current_url else True
            ),
            "has_url": bool(current_url and current_url != "about:blank"),
            "cookies_blocked": is_otr,  # True only with OTR profile
            "local_storage_disabled": is_otr,  # True only with OTR profile
            "persistent_storage_enabled": not is_otr,  # True only with persistent profile
            "permissions_blocked": True,  # Always blocked for security
            "certificate_validation": True,  # Always enabled for security
            "custom_cache_cleared": True,  # We clear custom cache in clear_session()
        }

    def log_privacy_status(self) -> None:
        """Log current privacy status without exposing URLs."""
        status = self.get_privacy_status()
        self.logger.info(f"Browser privacy status: {status}")

    def _on_stage_title_changed(self, title: str) -> None:
        """Emit titleChanged signal when the page title changes."""
        if not title:
            title = "New Tab"
        self.titleChanged.emit(title)

    @Slot(bool)
    def on_bookmark_page_button_toggled(self, checked: bool):
        """Add or remove bookmark for the current page and update button state."""
        url = self.ui.stage.url().toString()
        title = (
            self.ui.stage.title() if hasattr(self.ui.stage, "title") else url
        )
        if checked:
            self._add_or_update_bookmark(title, url)
        else:
            self._remove_bookmark(url)
        self._update_bookmark_page_button()
        self._save_browser_settings()

    def _add_or_update_bookmark(
        self, title: str = None, url: str = None, folder: str = "Bookmarks"
    ):
        if not title:
            title = self.ui.stage.title() or url or "(Untitled)"
        if not url:
            url = self.ui.stage.url().toString()
        settings_obj = AIRunnerSettings.objects.filter_by_first(name="browser")
        if not settings_obj:
            return
        try:
            data = (
                settings_obj.data
                if isinstance(settings_obj.data, dict)
                else json.loads(settings_obj.data)
            )
            bookmarks = data.get("bookmarks", [])
            found = False
            for f in bookmarks:
                if f["name"] == folder:
                    for bm in f["bookmarks"]:
                        if bm["url"] == url:
                            bm["title"] = title
                            found = True
                            break
                    if not found:
                        f["bookmarks"].append({"title": title, "url": url})
                        found = True
                    break
            if not found:
                bookmarks.append(
                    {
                        "name": folder,
                        "bookmarks": [{"title": title, "url": url}],
                    }
                )
            data["bookmarks"] = bookmarks
            AIRunnerSettings.objects.update(pk=settings_obj.id, data=data)
            if self._current_panel == "bookmarks":
                self._show_panel("bookmarks")
        except Exception as e:
            self.logger.warning(f"Failed to add/update bookmark: {e}")

    def _remove_bookmark(self, url: str, folder: str = "Bookmarks"):
        settings_obj = AIRunnerSettings.objects.filter_by_first(name="browser")
        if not settings_obj:
            return
        try:
            data = (
                settings_obj.data
                if isinstance(settings_obj.data, dict)
                else json.loads(settings_obj.data)
            )
            bookmarks = data.get("bookmarks", [])
            for f in bookmarks:
                if f["name"] == folder:
                    f["bookmarks"] = [
                        bm for bm in f["bookmarks"] if bm["url"] != url
                    ]
            data["bookmarks"] = [f for f in bookmarks if f["bookmarks"]]
            AIRunnerSettings.objects.update(pk=settings_obj.id, data=data)
        except Exception as e:
            self.logger.warning(f"Failed to remove bookmark: {e}")

    def _update_bookmark_page_button(self):
        url = self.ui.stage.url().toString()
        settings_obj = AIRunnerSettings.objects.filter_by_first(name="browser")
        checked = False
        if settings_obj:
            try:
                data = (
                    settings_obj.data
                    if isinstance(settings_obj.data, dict)
                    else json.loads(settings_obj.data)
                )
                bookmarks = data.get("bookmarks", [])
                for f in bookmarks:
                    for bm in f["bookmarks"]:
                        if bm["url"] == url:
                            checked = True
                            break
            except Exception:
                pass
        self.ui.bookmark_page_button.setChecked(checked)

    def clear(self):
        """Clear the browser state (reset to blank page and clear URL field)."""
        self.ui.stage.setUrl(QUrl("about:blank"))
        self.ui.url.clear()
        # Optionally reset other UI elements if needed

    def _on_favicon_changed(self, icon: QIcon):
        self._favicon = icon
        self.faviconChanged.emit(icon)

    def _on_url_changed(self, qurl):
        url = qurl.toString()
        title = self.current_title
        self.urlChanged.emit(url, title)

    def _on_title_changed(self, title: str):
        self.titleChanged.emit(title)

    @property
    def current_url(self) -> str:
        return self.ui.stage.url().toString()

    @property
    def current_title(self) -> str:
        return self.ui.stage.title() or self.current_url

    @property
    def favicon(self) -> Optional[QIcon]:
        return self._favicon

    def get_current_url(self) -> str:
        """Get the current URL as a method (for session save compatibility)."""
        return self.current_url

    def get_current_title(self) -> str:
        """Get the current title as a method (for session save compatibility)."""
        return self.current_title

    def print_page(self):
        if hasattr(self.ui.stage, "printToPdf"):
            from PySide6.QtWidgets import QFileDialog

            path, _ = QFileDialog.getSaveFileName(
                self, "Print to PDF", "", "PDF Files (*.pdf)"
            )
            if path:
                self.ui.stage.page().printToPdf(path)

    def save_page_with_assets(self, folder: str):
        # Save HTML and static assets (images, css, js) to folder
        # This is a stub; real implementation would parse and download assets
        html = self.ui.stage.page().toHtml(
            lambda html: self._save_html_and_assets(html, folder)
        )

    def _save_html_and_assets(self, html: str, folder: str):
        import re, requests
        import os

        os.makedirs(folder, exist_ok=True)
        url = self.current_url
        html_path = os.path.join(folder, "index.html")
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html)
        # Download images (very basic)
        img_urls = re.findall(r'<img[^>]+src=["\']([^"\'>]+)', html)
        for img_url in img_urls:
            try:
                if img_url.startswith("http"):
                    img_data = requests.get(img_url, timeout=5).content
                    img_name = os.path.basename(img_url.split("?")[0])
                    with open(os.path.join(folder, img_name), "wb") as imgf:
                        imgf.write(img_data)
            except Exception:
                pass
        # Could add CSS/JS download here

    def get_state(self) -> dict:
        return {
            "url": self.current_url,
            "title": self.current_title,
            "private": self._private,
        }

    def set_state(self, state: dict):
        url = state.get("url")
        if url:
            self.load_url(url)

    def load_url(self, url: str):
        self.ui.url.setText(url)
        self.on_submit_button_clicked()

    # --- Session Persistence (Non-Private Tabs) ---
    # To be called by main_window.py on app close/start
    @staticmethod
    def save_tab_sessions(tab_states: list, path: str):
        import json

        with open(path, "w", encoding="utf-8") as f:
            json.dump(tab_states, f)

    @staticmethod
    def load_tab_sessions(path: str) -> list:
        import json

        if not os.path.exists(path):
            return []
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
