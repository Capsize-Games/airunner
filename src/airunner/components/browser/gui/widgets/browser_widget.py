import json
from typing import Dict
from airunner.components.browser.gui.widgets.templates.browser_ui import (
    Ui_browser,
)
from airunner.enums import SignalCode
from airunner.components.tools.web_content_extractor import WebContentExtractor

from PySide6.QtCore import Slot, QObject
from PySide6.QtWebChannel import QWebChannel
from airunner.components.application.gui.widgets.base_widget import BaseWidget
from airunner.components.settings.data.airunner_settings import (
    AIRunnerSettings,
)
from PySide6.QtCore import QTimer
from PySide6.QtCore import Signal
from PySide6.QtGui import QIcon

from airunner.components.browser.gui.widgets.mixins.session_persistence_mixin import (
    SessionPersistenceMixin,
)
from airunner.components.browser.gui.widgets.mixins.privacy_mixin import (
    PrivacyMixin,
)
from airunner.components.browser.gui.widgets.mixins.panel_mixin import (
    PanelMixin,
)
from airunner.components.browser.gui.widgets.mixins.navigation_mixin import (
    NavigationMixin,
)
from airunner.components.browser.gui.widgets.mixins.summarization_mixin import (
    SummarizationMixin,
)
from airunner.components.browser.gui.widgets.mixins.cache_mixin import (
    CacheMixin,
)
from airunner.components.browser.gui.widgets.mixins.ui_setup_mixin import (
    UISetupMixin,
)
from airunner.components.browser.utils import normalize_url
import re
import os
import hashlib
from PySide6.QtCore import QUrl, Slot
from airunner.enums import SignalCode


class BrowserWidgetHandler(QObject):
    """Handles communication between JavaScript and the browser widget for generic widget commands."""

    widgetCommandReceived = Signal(str)

    def __init__(self, browser_widget):
        super().__init__()
        self.browser_widget = browser_widget

    @Slot(str)
    def handleCommand(self, command_json):
        """Handle commands from JavaScript (generic widget communication)."""
        try:
            command_data = json.loads(command_json)
            command = command_data.get("command", "")
            data = command_data.get("data", {})
            message_type = command_data.get(
                "type", "widget_command"
            )  # Use generic widget_command as default

            # Emit signal for other components to handle specific commands
            self.browser_widget.emit_signal(
                SignalCode.WIDGET_COMMAND_SIGNAL,
                {"command": command, "data": data, "type": message_type},
            )

            # Send generic response back to JavaScript
            self.browser_widget._send_response(
                "command_received",
                f"Command '{command}' processed successfully",
            )
        except Exception as e:
            self.browser_widget._send_response(
                "command_error", f"Error processing command: {str(e)}"
            )


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

    titleChanged = Signal(str)
    urlChanged = Signal(str, str)  # url, title
    faviconChanged = Signal(QIcon)
    widget_class_ = Ui_browser
    icons = [
        ("star", "bookmark_page_button"),
        ("eye-off", "private_browse_button"),
        ("chevron-up", "submit_button"),
        ("refresh-cw", "refresh_button"),
        ("arrow-left-circle", "back_button"),
        ("arrow-right-circle", "next_button"),
        ("bookmark", "bookmark_button"),
        ("clock", "history_button"),
        ("align-justify", "plaintext_button"),
        ("list", "summarize_button"),
        ("trash-2", "clear_data_button"),
        ("dice-game-icon", "random_button"),
    ]

    def __init__(self, *args, private: bool = False, **kwargs):
        self._favicon = None
        self._private = private
        self.registered = False
        self._profile = None
        self._profile_page = None
        self._private_browsing_enabled = False
        self._random_user_agent = False
        self._current_panel = None
        self.signal_handlers = {
            SignalCode.BROWSER_NAVIGATE_SIGNAL: self.on_browser_navigate
        }
        self.splitters = ["splitter"]
        super().__init__(*args, **kwargs)
        self._setup_ui()
        self._setup_widget_communication()
        self.ui.stage.loadFinished.connect(self._on_page_load_finished)

    def _setup_widget_communication(self):
        """Set up WebChannel for JavaScript-Python communication."""
        try:
            # Create widget handler
            self.widget_handler = BrowserWidgetHandler(self)

            # Create WebChannel
            self.channel = QWebChannel()
            # Register the widget handler
            self.channel.registerObject("widgetHandler", self.widget_handler)

            # Set WebChannel on the page
            self.ui.stage.page().setWebChannel(self.channel)
        except Exception as e:
            print(f"Error setting up widget communication: {e}")

    def _send_response(self, response_type, message):
        """Send a response back to JavaScript (generic response format)."""
        try:
            # Properly escape the values using JSON
            response_data = {
                "type": "widget_response",
                "response_type": response_type,
                "message": message,
                "timestamp": "Date.now()",  # This will be handled specially
            }

            # Create safe JavaScript code with proper JSON escaping
            script = f"""
            window.postMessage({{
                type: {json.dumps(response_data["type"])},
                response_type: {json.dumps(response_data["response_type"])},
                message: {json.dumps(response_data["message"])},
                timestamp: Date.now()
            }}, '*');
            """
            self.ui.stage.page().runJavaScript(script)
        except Exception as e:
            print(f"Error sending response: {e}")

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

    @Slot()
    def on_next_button_clicked(self) -> None:
        self.ui.stage.forward()

    @Slot()
    def on_back_button_clicked(self) -> None:
        self.ui.stage.back()

    @Slot()
    def on_refresh_button_clicked(self) -> None:
        self.reload()

    @Slot()
    def on_submit_button_clicked(self) -> None:
        url = self.ui.url.text().strip()
        if not url:
            self.logger.warning("No URL provided")
            return
        original_url = url
        if url.startswith("local:"):
            self.logger.info("Redirecting to local HTTP server for '%s'", url)
            local_name = url[len("local:") :].strip()
            if not local_name:
                self.logger.warning(
                    "No local file specified after 'local:' scheme."
                )
                return
            # Redirect to the HTTP server
            http_url = f"https://127.0.0.1:5005/{local_name}"
            self.ui.stage.setUrl(QUrl(http_url))
            self.ui.url.setText(http_url)
            return
        # Only upgrade to HTTPS if not already tried HTTP fallback
        if not url.startswith("http://") and not url.startswith("https://"):
            url = f"https://{url}"
        if url.startswith("http://"):
            # If we already tried HTTP and failed, don't loop
            if url == self._last_attempted_http_url:
                self.logger.warning("HTTP fallback also failed.")
                self._last_attempted_http_url = None
                return
            url = url.replace("http://", "https://", 1)
            self.logger.info("Upgraded insecure URL to HTTPS")
        if url != original_url:
            self.ui.url.setText(url)
        self.ui.url.clearFocus()
        pattern = re.compile(
            r"^https://([\w.-]+|\d{1,3}(?:\.\d{1,3}){3})(?::\d+)?(?:[/?#][^\s]*)?$"
        )
        if pattern.match(url):
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
                self._last_failed_https_url = (
                    url if url.startswith("https://") else None
                )
                self._last_attempted_http_url = None
                self.ui.stage.setUrl(QUrl(url))
        else:
            self.logger.warning("Invalid or insecure URL rejected")
            self.ui.url.setStyleSheet(
                "QLineEdit { background: #331111; color: #ff9999; }"
            )

    @Slot(bool)
    def _on_page_load_finished(self, success: bool):
        if not success:
            return

        # Inject QWebChannel script for JavaScript communication
        self._inject_webchannel_script()

        self.ui.stage.page().toHtml(self._on_html_ready)

    @Slot(bool)
    def on_private_browse_button_toggled(self, checked: bool) -> None:
        self._set_private_browsing(checked)
        self._save_browser_settings()

    @Slot(bool)
    def on_bookmark_button_toggled(self, checked: bool):
        if checked:
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

    def _inject_webchannel_script(self):
        """Inject QWebChannel JavaScript for communication."""
        try:
            # Inject the QWebChannel script
            webchannel_script = """
            (function() {
                if (typeof QWebChannel === 'undefined') {
                    // Load QWebChannel from Qt resources
                    var script = document.createElement('script');
                    script.src = 'qrc:///qtwebchannel/qwebchannel.js';
                    script.onload = function() {
                        console.log('QWebChannel script loaded');
                        // Trigger custom event to notify our game script
                        window.dispatchEvent(new Event('qwebchannelready'));
                    };
                    script.onerror = function() {
                        console.log('QWebChannel script failed to load, using fallback');
                    };
                    document.head.appendChild(script);
                } else {
                    console.log('QWebChannel already available');
                }
            })();
            """
            self.ui.stage.page().runJavaScript(webchannel_script)
        except Exception as e:
            print(f"Error injecting WebChannel script: {e}")

    def on_browser_navigate(self, data: Dict):
        """Handle browser navigation requests."""
        url = data.get("url")
        url = normalize_url(url) if url else url
        if hasattr(self.ui, "stage"):
            self.ui.stage.setUrl(url)
        else:
            self.logger.warning(
                "Browser stage not initialized for navigation."
            )

    def _on_html_ready(self, html: str):
        """Handle HTML content when ready from QWebEnginePage."""
        content = WebContentExtractor.extract_markdown(html)
        if content:
            markdown = "# URL: " + self.ui.stage.url().toString() + "\n\n"
            markdown += "## Title: " + self.ui.stage.title() + "\n\n"
            markdown += "## Content:\n\n"
            markdown += content
            self.emit_signal(
                SignalCode.BROWSER_EXTRA_CONTEXT,
                {
                    "plaintext": markdown,
                    "url": self.ui.stage.url().toString(),
                },
            )

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
        # Ensure the page cache always has the latest URL for restoration
        if hasattr(self, "_page_cache"):
            self._page_cache["url"] = str(url.toString())

    def _on_title_changed(self, title):
        """Emit titleChanged signal when the page title changes."""
        self.titleChanged.emit(title)

    def _on_stage_title_changed(self, title):
        """Update the tab title in the tab widget when the page title changes."""
        if hasattr(self.ui, "browser_tab_widget") and hasattr(self.ui, "tab"):
            self.ui.browser_tab_widget.setTabText(
                self.ui.browser_tab_widget.indexOf(self.ui.tab), title
            )

    def reload(self):
        # Default reload behavior - let the HTTP server handle template rendering
        self.ui.stage.reload()

    def clear(self):
        """Reset the browser tab to a blank state (blank page, clear address bar, clear cache)."""
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

    def closeEvent(self, event):
        """Override removed: tab close safety is now handled at the tab manager level."""
        event.accept()

    def safe_close(self, on_safe: callable = None):
        """Ensure QWebEngineView is safely unloaded before widget deletion. Calls on_safe() when safe to delete."""
        if hasattr(self.ui, "stage"):
            stage = self.ui.stage
            if stage.url().toString() == "about:blank":
                if on_safe:
                    QTimer.singleShot(0, on_safe)
                return

            def on_blank_loaded(ok):
                try:
                    stage.loadFinished.disconnect(on_blank_loaded)
                except Exception:
                    pass
                if on_safe:
                    QTimer.singleShot(0, on_safe)

            try:
                stage.stop()
                stage.loadFinished.connect(on_blank_loaded)
                stage.setUrl("about:blank")
            except Exception:
                if on_safe:
                    on_safe()
        else:
            if on_safe:
                on_safe()
