"""
UISetupMixin for BrowserWidget.
Handles UI setup, signal connections, and layout logic.

Google Python Style Guide applies.
"""

from PySide6.QtWidgets import QVBoxLayout
from PySide6.QtCore import QSettings
from PySide6.QtCore import Slot
import json

from airunner.components.browser.data.settings import BrowserSettings
from airunner.components.settings.data.airunner_settings import (
    AIRunnerSettings,
)
from airunner.components.browser.gui.enums import BrowserType, BrowserOS
from airunner.components.browser.gui.widgets.items_widget import ItemsWidget


class UISetupMixin:
    @Slot(bool)
    def on_bookmark_page_button_toggled(self, checked: bool):
        """Add or remove the current page from bookmarks when the star button is toggled."""
        url = self.ui.url.text().strip()
        title = self.ui.stage.title().strip() or url
        if not url:
            return
        # Use PanelMixin/bookmark logic for DRYness
        if checked:
            if not self.is_page_bookmarked(url):
                self.add_bookmark(url, title)
        else:
            self.remove_bookmark(url)
        # Update UI state to reflect bookmark status
        self.ui.bookmark_page_button.blockSignals(True)
        self.ui.bookmark_page_button.setChecked(self.is_page_bookmarked(url))
        self.ui.bookmark_page_button.blockSignals(False)

    def on_load_finished(self, ok: bool):
        """Slot for QWebEngineView loadFinished signal. Updates security indicators and tab title."""
        self._update_security_indicators()
        if hasattr(self, "_on_stage_title_changed"):
            self._on_stage_title_changed(self.ui.stage.title())

    def _setup_ui(self):
        self._favicon = None
        self._private = False
        self.registered = False
        self._profile = None
        self._profile_page = None
        self._private_browsing_enabled = False
        self._random_user_agent = False
        self._current_panel = None
        self.ui.stage.iconChanged.connect(self._on_favicon_changed)
        self.ui.stage.urlChanged.connect(self._on_url_changed)
        self.ui.stage.titleChanged.connect(self._on_title_changed)
        self.ui.stage.titleChanged.connect(self._on_stage_title_changed)
        self.ui.stage.loadFinished.connect(self.on_load_finished)
        self._load_browser_settings()
        if not hasattr(self, "_ui_indicators_set"):
            self._update_private_browsing_icon(self._private_browsing_enabled)
            self._update_private_browsing_styling(
                self._private_browsing_enabled
            )
            self._ui_indicators_set = True
        self.ui.stage.setPage(self.profile_page)
        self.set_flags()
        self._page_cache = {
            k: None for k in ("html", "plaintext", "summary", "url")
        }
        self._current_display_mode = "html"
        self.ui.stage.setStyleSheet("background: #111;")
        self.ui.stage.page().setBackgroundColor("#111111")

        # User agent browser/os setup
        try:
            browser_type = BrowserType[self.browser_settings["browser_type"]]
        except KeyError:
            browser_type = BrowserType.CHROME
        try:
            browser_os = BrowserOS[self.browser_settings["browser_os"]]
        except KeyError:
            browser_os = BrowserOS.WINDOWS
        for widget, enum, default in [
            (self.ui.user_agent_browser, BrowserType, browser_type),
            (self.ui.user_agent_os, BrowserOS, browser_os),
        ]:
            widget.blockSignals(True)
            widget.clear()
            widget.addItems([e.value for e in enum])
            widget.setCurrentText(default.value)
            widget.blockSignals(False)

        # Random user agent button setup
        self.ui.random_button.blockSignals(True)
        self.ui.random_button.setChecked(
            self.browser_settings["random_user_agent"]
        )
        self.ui.random_button.blockSignals(False)

        # Connect Enter/Return in URL bar to submit handler
        self.ui.url.returnPressed.connect(self.on_submit_button_clicked)

        self.log_privacy_status()
        self.ui.left_panel.hide()
        self.ui.right_panel.hide()
        self.bookmarks_widget = ItemsWidget(self.ui.left_panel)
        self.history_widget = ItemsWidget(self.ui.left_panel)
        self.bookmarks_widget.hide()
        self.history_widget.hide()
        left_layout = self.ui.left_panel.layout() or QVBoxLayout(
            self.ui.left_panel
        )
        for w in (self.bookmarks_widget, self.history_widget):
            left_layout.addWidget(w)
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
            total = self.ui.splitter.size().width() or 800
            left = 250
            center = total - left
            self.ui.splitter.setSizes([left, center, 0])

    def _load_browser_settings(self):
        settings_obj = AIRunnerSettings.objects.filter_by_first(name="browser")
        if not settings_obj:
            return
        try:
            settings_data = (
                settings_obj.data
                if isinstance(settings_obj.data, dict)
                else json.loads(settings_obj.data)
            )
            browser_settings = BrowserSettings(**settings_data)
            # Map of browser_settings fields to (UI setter, value)
            ui_updates = [
                (
                    lambda v: setattr(self, "_private_browsing_enabled", v),
                    browser_settings.private_browsing,
                ),
                (
                    self.ui.private_browse_button.setChecked,
                    browser_settings.private_browsing,
                ),
                (
                    self._update_private_browsing_icon,
                    browser_settings.private_browsing,
                ),
                (
                    self._update_private_browsing_styling,
                    browser_settings.private_browsing,
                ),
                (lambda v: setattr(self, "_ui_indicators_set", True), True),
                (
                    self.ui.user_agent_browser.setCurrentText,
                    browser_settings.browser_type,
                ),
                (
                    self.ui.user_agent_os.setCurrentText,
                    browser_settings.browser_os,
                ),
                (
                    lambda v: setattr(self, "_random_user_agent", v),
                    browser_settings.random_user_agent,
                ),
            ]
            for setter, value in ui_updates:
                setter(value)
            # Optional pushButton
            if hasattr(self.ui, "pushButton"):
                self.ui.pushButton.setChecked(
                    browser_settings.random_user_agent
                )
        except Exception as e:
            self.logger.warning(f"Failed to load browser settings: {e}")
            self._private_browsing_enabled = False
            self.ui.private_browse_button.setChecked(False)
            self._update_private_browsing_icon(False)
            self._update_private_browsing_styling(False)
            self._ui_indicators_set = True
