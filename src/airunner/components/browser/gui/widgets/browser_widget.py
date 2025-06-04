import json
from airunner.components.browser.gui.enums import BrowserOS, BrowserType
from airunner.components.browser.gui.widgets.templates.browser_ui import (
    Ui_browser,
)
from airunner.enums import SignalCode

from PySide6.QtCore import Slot
from airunner.gui.widgets.base_widget import BaseWidget
from airunner.data.models.airunner_settings import AIRunnerSettings
from PySide6.QtWidgets import QVBoxLayout
from airunner.components.browser.gui.widgets.items_widget import ItemsWidget
from PySide6.QtCore import QSettings

from .mixins.session_persistence_mixin import SessionPersistenceMixin
from .mixins.privacy_mixin import PrivacyMixin
from .mixins.panel_mixin import PanelMixin
from .mixins.navigation_mixin import NavigationMixin
from .mixins.summarization_mixin import SummarizationMixin
from .mixins.cache_mixin import CacheMixin
from .mixins.ui_setup_mixin import UISetupMixin


class BrowserWidget(
    UISetupMixin,
    SessionPersistenceMixin,
    PrivacyMixin,
    PanelMixin,
    NavigationMixin,
    SummarizationMixin,
    CacheMixin,
    BaseWidget,
):
    """Widget that displays a single browser instance (address bar, navigation, webview, etc.).

    Inherits mixins for modular browser logic.
    """

    from PySide6.QtCore import Signal
    from PySide6.QtGui import QIcon, QPixmap

    titleChanged = Signal(str)
    urlChanged = Signal(str, str)  # url, title
    faviconChanged = Signal(QIcon)
    widget_class_ = Ui_browser

    def __init__(self, *args, private: bool = False, **kwargs):
        self._favicon = None
        self._private = False
        self.registered = False
        self._profile = None
        self._profile_page = None
        self._private_browsing_enabled = False
        self._random_user_agent = False
        self._current_panel = None
        self.signal_handlers = {
            SignalCode.BROWSER_NAVIGATE_SIGNAL: self.on_browser_navigate
        }
        super().__init__(*args, **kwargs)
        self._setup_ui()

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

    @Slot(bool)
    def on_private_browse_button_toggled(self, checked: bool) -> None:
        self._set_private_browsing(checked)
        self._save_browser_settings()

    @Slot(bool)
    def on_bookmark_button_toggled(self, checked: bool):
        if checked:
            self.ui.history_button.setChecked(False)
            self._show_panel("bookmarks")
        else:
            self._show_panel(None)

    @Slot(bool)
    def on_history_button_toggled(self, checked: bool):
        if checked:
            self.ui.bookmark_button.setChecked(False)
            self._show_panel("history")
        else:
            self._show_panel(None)

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

    def _on_favicon_changed(self, icon):
        """Update the favicon for the current tab."""
        self.faviconChanged.emit(icon)
        if hasattr(self.ui, "browser_tab_widget") and hasattr(self.ui, "tab"):
            self.ui.browser_tab_widget.setTabIcon(
                self.ui.browser_tab_widget.indexOf(self.ui.tab), icon
            )

    def _on_url_changed(self, url):
        """Update the URL field when the page URL changes."""
        self.urlChanged.emit(url.toString(), self.ui.stage.title())
        self.ui.url.setText(url.toString())

    def _on_title_changed(self, title):
        """Emit titleChanged signal when the page title changes."""
        self.titleChanged.emit(title)

    def _on_stage_title_changed(self, title):
        """Update the tab title in the tab widget when the page title changes."""
        if hasattr(self.ui, "browser_tab_widget") and hasattr(self.ui, "tab"):
            self.ui.browser_tab_widget.setTabText(
                self.ui.browser_tab_widget.indexOf(self.ui.tab), title
            )

    def clear(self):
        """Reset the browser tab to a blank state (blank page, clear address bar, clear cache)."""
        from PySide6.QtWebEngineWidgets import QWebEngineView

        if hasattr(self, "ui") and hasattr(self.ui, "stage"):
            try:
                self.ui.stage.stop()
                self.ui.stage.setUrl("about:blank")
            except Exception:
                pass
        if hasattr(self, "ui") and hasattr(self.ui, "url"):
            self.ui.url.setText("")
        self._page_cache = {
            k: None for k in ("html", "plaintext", "summary", "url")
        }
        self._current_display_mode = "html"
        if hasattr(self, "_show_panel"):
            self._show_panel(None)
        # Reset tab title
        if hasattr(self.ui, "browser_tab_widget"):
            idx = (
                self.ui.browser_tab_widget.indexOf(self.ui.tab)
                if hasattr(self.ui, "tab")
                else -1
            )
            if idx != -1:
                self.ui.browser_tab_widget.setTabText(idx, "New Tab")
        # Reset bookmark/star button
        if hasattr(self.ui, "bookmark_page_button"):
            self.ui.bookmark_page_button.setChecked(False)
