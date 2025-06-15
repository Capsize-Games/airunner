"""Browser Control Mixin for MainWindow.

This mixin provides full control over the browser functionality in the main window,
including tabbed browsing, keyboard shortcuts, session management, and all browser operations.
"""

from typing import List, Optional, Dict, Any
from PySide6.QtCore import QTimer, Slot
from PySide6.QtGui import QShortcut, QKeySequence, QIcon
from PySide6.QtWidgets import QTabWidget
from PySide6.QtPrintSupport import QPrintDialog, QPrinter
from airunner.components.browser.gui.widgets.browser_widget import (
    BrowserWidget,
)
from airunner.components.settings.data.airunner_settings import AIRunnerSettings
import json


class BrowserControlMixin:
    """Mixin to provide comprehensive browser control functionality to MainWindow.

    Features:
    - Tabbed browsing with keyboard shortcuts (Ctrl+T, Ctrl+W, Ctrl+Shift+T)
    - Tab management (open, close, navigate between tabs, restore closed tabs)
    - Session restore (tabs and their state restored on restart)
    - Private browsing control across all tabs with visual indicators
    - Print support (Ctrl+P)
    - Navigation controls (back, forward, refresh, go to URL)
    - Bookmark and history management
    - Middle mouse button tab closing
    - Dark purple styling for private browsing tabs
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._browser_tabs: List[BrowserWidget] = []
        self._current_browser_tab: Optional[BrowserWidget] = None
        self._private_browsing_mode: bool = False
        self._closed_tabs_history: List[Dict[str, Any]] = (
            []
        )  # Track closed tabs for restore
        self._session_restore_timer: QTimer = QTimer()
        self._session_restore_timer.timeout.connect(self._save_browser_session)
        self._session_restore_timer.start(
            30000
        )  # Save session every 30 seconds
        self.shortcuts = {
            "Ctrl+T": self.new_browser_tab,
            "Ctrl+W": self.close_current_browser_tab,
            "Ctrl+Shift+T": self.restore_last_closed_tab,
            "Ctrl+P": self.print_current_page,
            "Shift+Ctrl+P": self.toggle_private_browsing,
            "Alt+Left": self.navigate_back,
            "Alt+Right": self.navigate_forward,
            "Alt+Tab": self.cycle_browser_tabs,
            "SHIFT+Alt+Tab": self.cycle_browser_tabs_reverse,
            "F5": self.refresh_current_page,
            "Ctrl+R": self.refresh_current_page,
        }

    def initialize_browser_controls(self):
        """Initialize browser controls and shortcuts. Call this after UI setup."""
        self._setup_browser_shortcuts()
        self._setup_browser_events()
        self._restore_browser_session()

    def _setup_browser_shortcuts(self):
        """Setup keyboard shortcuts for browser control."""
        for key, action in self.shortcuts.items():
            shortcut = QShortcut(QKeySequence(key), self)
            shortcut.activated.connect(action)

    def _setup_browser_events(self):
        """Setup browser tab widget events."""
        if hasattr(self.ui, "browser"):
            self.ui.browser.tabCloseRequested.connect(self.close_browser_tab)
            self.ui.browser.currentChanged.connect(
                self._on_browser_tab_changed
            )
            # Enable middle mouse button tab closing
            self.ui.browser.setTabsClosable(True)

    def _get_browser_tab_widget(self) -> QTabWidget:
        """Get the browser tab widget from the UI."""
        return getattr(self.ui, "browser", None)

    # Tab Management Methods

    @Slot()
    def new_browser_tab(
        self, url: str = "", private: bool = None
    ) -> BrowserWidget:
        """Create a new browser tab.

        Args:
            url: Initial URL to load
            private: Use private browsing (None = use current mode)

        Returns:
            The new BrowserWidget instance
        """
        browser_widget = self._get_browser_tab_widget()
        if not browser_widget:
            return None

        # Use current private browsing mode if not specified
        if private is None:
            private = self._private_browsing_mode

        # Create new browser widget
        new_tab = BrowserWidget(private=private)

        # Connect signals
        new_tab.titleChanged.connect(
            lambda title, tab=new_tab: self._update_tab_title(tab, title)
        )
        new_tab.faviconChanged.connect(
            lambda icon, tab=new_tab: self._update_tab_icon(tab, icon)
        )

        # Add to tab widget
        tab_index = browser_widget.addTab(new_tab, "New Tab")
        browser_widget.setCurrentIndex(tab_index)

        # Apply private browsing styling if needed
        if private:
            self._apply_private_tab_styling(browser_widget, tab_index)

        # Track the tab
        self._browser_tabs.append(new_tab)
        self._current_browser_tab = new_tab

        # Load initial URL if provided
        if url:
            new_tab.load_url(url)

        # Focus the URL bar for immediate typing
        QTimer.singleShot(100, lambda: self._focus_url_bar(new_tab))

        # Ensure Ctrl+Tab cycles tabs even when webview is focused
        from PySide6.QtGui import QShortcut, QKeySequence
        ctrl_tab_shortcut = QShortcut(QKeySequence("Ctrl+Tab"), new_tab.ui.stage)
        ctrl_tab_shortcut.activated.connect(self.cycle_browser_tabs)

        return new_tab

    def _focus_url_bar(self, tab: BrowserWidget):
        """Focus and select all text in the URL bar of the given tab."""
        try:
            if hasattr(tab, "ui") and hasattr(tab.ui, "url"):
                tab.ui.url.setFocus()
                tab.ui.url.selectAll()
        except Exception as e:
            # Silently handle URL bar focus failure
            pass

    def _apply_private_tab_styling(
        self, browser_widget: QTabWidget, tab_index: int
    ):
        """Apply dark purple styling to indicate private browsing tab."""
        try:
            # Set dark purple background for private browsing tabs
            browser_widget.tabBar().setTabData(tab_index, "private")
            self._update_tab_styling(
                browser_widget, tab_index, is_private=True
            )
        except Exception as e:
            print(f"Failed to apply private tab styling: {e}")

    def _update_tab_styling(
        self,
        browser_widget: QTabWidget,
        tab_index: int,
        is_private: bool = False,
    ):
        """Update tab styling based on private browsing status."""
        try:
            tab_bar = browser_widget.tabBar()
            if is_private:
                # Dark purple styling for private tabs
                style = """
                QTabBar::tab:selected {
                    background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                                stop: 0 #6B46C1, stop: 1 #553C9A);
                    color: white;
                    border: 2px solid #8B5CF6;
                }
                QTabBar::tab:!selected {
                    background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                                stop: 0 #4C1D95, stop: 1 #3C1366);
                    color: #E9D5FF;
                    border: 1px solid #7C3AED;
                }
                QTabBar::tab:hover:!selected {
                    background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                                stop: 0 #5B21B6, stop: 1 #4C1D95);
                }
                """
            else:
                # Reset to default styling for regular tabs
                style = ""

            # Apply the style to the specific tab
            if hasattr(tab_bar, "setStyleSheet"):
                # Note: This applies to all tabs, but we'll use tabData to track private status
                current_style = tab_bar.styleSheet()
                if is_private and "QTabBar::tab" not in current_style:
                    tab_bar.setStyleSheet(current_style + style)
                elif not is_private and any(
                    self._is_tab_private(browser_widget, i)
                    for i in range(browser_widget.count())
                ):
                    # Only reset if no other private tabs exist
                    if not any(
                        browser_widget.tabBar().tabData(i) == "private"
                        for i in range(browser_widget.count())
                        if i != tab_index
                    ):
                        tab_bar.setStyleSheet("")
        except Exception as e:
            print(f"Failed to update tab styling: {e}")

    def _is_tab_private(
        self, browser_widget: QTabWidget, tab_index: int
    ) -> bool:
        """Check if a tab is in private browsing mode."""
        try:
            tab_widget = browser_widget.widget(tab_index)
            if isinstance(tab_widget, BrowserWidget):
                return getattr(tab_widget, "_private", False)
            return browser_widget.tabBar().tabData(tab_index) == "private"
        except Exception:
            return False

    def _update_all_tab_styling(self):
        """Update styling for all tabs based on their private browsing status."""
        browser_widget = self._get_browser_tab_widget()
        if not browser_widget:
            return

        has_private_tabs = False
        for i in range(browser_widget.count()):
            is_private = self._is_tab_private(browser_widget, i)
            if is_private:
                has_private_tabs = True
                self._apply_private_tab_styling(browser_widget, i)

        # Apply or remove the global private tab styling
        if has_private_tabs:
            self._apply_global_private_styling(browser_widget)
        else:
            self._remove_global_private_styling(browser_widget)

    def _apply_global_private_styling(self, browser_widget: QTabWidget):
        """Apply global styling for private browsing tabs."""
        style = """
        QTabBar::tab[data="private"]:selected {
            background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                        stop: 0 #6B46C1, stop: 1 #553C9A);
            color: white;
            border: 2px solid #8B5CF6;
            border-bottom: none;
        }
        QTabBar::tab[data="private"]:!selected {
            background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                        stop: 0 #4C1D95, stop: 1 #3C1366);
            color: #E9D5FF;
            border: 1px solid #7C3AED;
            border-bottom: none;
        }
        QTabBar::tab[data="private"]:hover:!selected {
            background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                        stop: 0 #5B21B6, stop: 1 #4C1D95);
        }
        """
        current_style = browser_widget.tabBar().styleSheet()
        if 'data="private"' not in current_style:
            browser_widget.tabBar().setStyleSheet(current_style + style)

    def _remove_global_private_styling(self, browser_widget: QTabWidget):
        """Remove global private browsing styling when no private tabs exist."""
        current_style = browser_widget.tabBar().styleSheet()
        # Remove private styling sections
        lines = current_style.split("\n")
        filtered_lines = []
        skip_block = False
        for line in lines:
            if 'data="private"' in line:
                skip_block = True
            elif skip_block and line.strip() == "}":
                skip_block = False
                continue
            elif not skip_block:
                filtered_lines.append(line)
        browser_widget.tabBar().setStyleSheet("\n".join(filtered_lines))

    @Slot(int)
    def close_browser_tab(self, index: int):
        """Close browser tab at given index, safely unloading QWebEngineView before deletion."""
        browser_widget = self._get_browser_tab_widget()
        if not browser_widget or index < 0 or index >= browser_widget.count():
            return

        # Get the widget before removing
        tab_widget = browser_widget.widget(index)

        # Don't close if it's the last tab - clear it instead
        if browser_widget.count() == 1:
            self.clear_current_browser_tab()
            return

        # Save tab info for restore functionality before closing
        if isinstance(tab_widget, BrowserWidget):
            url = ""
            title = "New Tab"
            private = getattr(tab_widget, "_private", False)
            try:
                if hasattr(tab_widget, "ui") and hasattr(
                    tab_widget.ui, "stage"
                ):
                    url = tab_widget.ui.stage.url().toString()
                    title = tab_widget.ui.stage.title()
            except Exception:
                pass
            tab_info = {"url": url, "title": title, "private": private}
            self._closed_tabs_history.append(tab_info)

        # Remove from tab widget and internal tracking
        def on_safe():
            browser_widget.removeTab(index)
            if tab_widget in self._browser_tabs:
                self._browser_tabs.remove(tab_widget)
            if self._current_browser_tab == tab_widget:
                self._current_browser_tab = (
                    self._browser_tabs[-1] if self._browser_tabs else None
                )
            tab_widget.deleteLater()

        if hasattr(tab_widget, "safe_close"):
            tab_widget.safe_close(on_safe)
        else:
            on_safe()

    @Slot()
    def close_current_browser_tab(self):
        """Close the currently active browser tab."""
        browser_widget = self._get_browser_tab_widget()
        if browser_widget:
            current_index = browser_widget.currentIndex()
            self.close_browser_tab(current_index)

    @Slot()
    def clear_current_browser_tab(self):
        """Clear the current browser tab (reset to blank state)."""
        if self._current_browser_tab:
            self._current_browser_tab.clear()

    @Slot()
    def restore_last_closed_tab(self):
        """Restore the most recently closed tab."""
        if not self._closed_tabs_history:
            self._show_browser_notification(
                "No recently closed tabs to restore."
            )
            return
        tab_info = self._closed_tabs_history.pop()
        print(f"TAB INFO FROM HISTORY {tab_info}")
        url = tab_info.get("url", "")
        private = tab_info.get("private", False)
        restored_tab = self.new_browser_tab(url=url, private=private)
        # Optionally set the tab title if needed (title is usually set by page load)
        # restored_tab.setWindowTitle(tab_info.get("title", "New Tab"))
        self._show_browser_notification(
            f"Restored tab: {tab_info.get('title', 'New Tab')}"
        )

    @Slot(int)
    def _on_browser_tab_changed(self, index: int):
        """Handle browser tab change."""
        browser_widget = self._get_browser_tab_widget()
        if browser_widget:
            current_widget = browser_widget.widget(index)
            self._current_browser_tab = (
                current_widget
                if isinstance(current_widget, BrowserWidget)
                else None
            )

    def _update_tab_title(self, tab: BrowserWidget, title: str):
        """Update tab title when page title changes."""
        browser_widget = self._get_browser_tab_widget()
        if browser_widget and tab:
            index = browser_widget.indexOf(tab)
            if index >= 0:
                # Truncate long titles
                display_title = (
                    title[:30] + "..." if len(title) > 30 else title
                )
                browser_widget.setTabText(index, display_title or "New Tab")

    def _update_tab_icon(self, tab: BrowserWidget, icon: QIcon):
        """Update tab icon when page favicon changes."""
        browser_widget = self._get_browser_tab_widget()
        if browser_widget and tab:
            index = browser_widget.indexOf(tab)
            if index >= 0:
                browser_widget.setTabIcon(index, icon)

    # Navigation Methods

    @Slot()
    def navigate_back(self):
        """Navigate back in current browser tab."""
        if self._current_browser_tab:
            self._current_browser_tab.go_back()

    @Slot()
    def navigate_forward(self):
        """Navigate forward in current browser tab."""
        if self._current_browser_tab:
            self._current_browser_tab.go_forward()

    @Slot()
    def cycle_browser_tabs(self):
        """Cycle through browser tabs."""
        browser_widget = self._get_browser_tab_widget()
        if not browser_widget:
            return

        current_index = browser_widget.currentIndex()
        next_index = (current_index + 1) % browser_widget.count()
        browser_widget.setCurrentIndex(next_index)

        # Update current tab reference
        self._current_browser_tab = browser_widget.widget(next_index)

    @Slot()
    def cycle_browser_tabs_reverse(self):
        """Cycle through browser tabs in reverse order."""
        browser_widget = self._get_browser_tab_widget()
        if not browser_widget:
            return

        current_index = browser_widget.currentIndex()
        next_index = (current_index - 1) % browser_widget.count()
        browser_widget.setCurrentIndex(next_index)

        # Update current tab reference
        self._current_browser_tab = browser_widget.widget(next_index)

    @Slot()
    def refresh_current_page(self):
        """Reload the current page."""
        if self._current_browser_tab:
            self._current_browser_tab.reload()
        else:
            self._show_browser_notification("No page to refresh")

    def navigate_to_url(self, url: str):
        """Navigate current tab to URL."""
        if self._current_browser_tab:
            self._current_browser_tab.load_url(url)
        else:
            # Create new tab if none exists
            self.new_browser_tab(url)

    def get_current_url(self) -> str:
        """Get the URL of the current browser tab."""
        if self._current_browser_tab:
            return self._current_browser_tab.get_current_url()
        return ""

    def get_current_title(self) -> str:
        """Get the title of the current browser tab."""
        if self._current_browser_tab:
            return self._current_browser_tab.get_current_title()
        return ""

    # Private Browsing Methods

    @Slot()
    def toggle_private_browsing(self):
        """Toggle private browsing mode for all tabs."""
        self._private_browsing_mode = not self._private_browsing_mode

        # Apply to all existing tabs
        for tab in self._browser_tabs:
            if hasattr(tab, "set_private_browsing"):
                tab.set_private_browsing(self._private_browsing_mode)

        # Update tab styling
        self._update_all_tab_styling()

        # Show notification
        mode_text = "enabled" if self._private_browsing_mode else "disabled"
        self._show_browser_notification(f"Private browsing {mode_text}")

    def set_private_browsing(self, enabled: bool):
        """Set private browsing mode."""
        self._private_browsing_mode = enabled

        # Apply to all existing tabs
        for tab in self._browser_tabs:
            if hasattr(tab, "set_private_browsing"):
                tab.set_private_browsing(enabled)

        # Update tab styling
        self._update_all_tab_styling()

    def is_private_browsing(self) -> bool:
        """Check if private browsing is enabled."""
        return self._private_browsing_mode

    # Bookmark and History Methods

    def add_bookmark(self, url: str = None, title: str = None):
        """Add current page to bookmarks."""
        if self._current_browser_tab:
            if hasattr(self._current_browser_tab, "add_bookmark"):
                self._current_browser_tab.add_bookmark(url, title)

    def show_bookmarks(self):
        """Show bookmarks panel."""
        if self._current_browser_tab:
            if hasattr(self._current_browser_tab, "show_bookmarks"):
                self._current_browser_tab.show_bookmarks()

    def show_history(self):
        """Show history panel."""
        if self._current_browser_tab:
            if hasattr(self._current_browser_tab, "show_history"):
                self._current_browser_tab.show_history()

    def clear_browsing_data(self):
        """Clear browsing data for current tab."""
        if self._current_browser_tab:
            if hasattr(self._current_browser_tab, "clear_browsing_data"):
                self._current_browser_tab.clear_browsing_data()

    # Print Methods

    @Slot()
    def print_current_page(self):
        """Print the current page to PDF."""
        if not self._current_browser_tab:
            self._show_browser_notification("No page to print")
            return

        try:
            # Create print dialog
            printer = QPrinter(QPrinter.HighResolution)
            printer.setOutputFormat(QPrinter.PdfFormat)
            printer.setOutputFileName("page.pdf")

            dialog = QPrintDialog(printer, self)
            if dialog.exec() == QPrintDialog.Accepted:
                # Print the current page
                if hasattr(self._current_browser_tab, "print_page"):
                    self._current_browser_tab.print_page(printer)
                else:
                    self._show_browser_notification(
                        "Print not supported for this page"
                    )
        except Exception as e:
            self._show_browser_notification(f"Print failed: {str(e)}")

    # Session Management Methods

    def _save_browser_session(self):
        """Save current browser session to settings."""
        if not hasattr(self.ui, "browser"):
            return

        browser_widget = self.ui.browser
        session_data = {
            "tabs": [],
            "current_tab": browser_widget.currentIndex(),
            "private_browsing": self._private_browsing_mode,
        }

        # Save each tab's state
        for i in range(browser_widget.count()):
            tab_widget = browser_widget.widget(i)
            if isinstance(tab_widget, BrowserWidget):
                tab_data = {
                    "url": (
                        tab_widget.get_current_url()
                        if hasattr(tab_widget, "get_current_url")
                        else ""
                    ),
                    "title": (
                        tab_widget.get_current_title()
                        if hasattr(tab_widget, "get_current_title")
                        else ""
                    ),
                    "private": getattr(tab_widget, "_private", False),
                }
                session_data["tabs"].append(tab_data)

        # Save to settings
        settings_obj = AIRunnerSettings.objects.filter_by_first(
            name="browser_session"
        )
        if settings_obj:
            AIRunnerSettings.objects.update(
                pk=settings_obj.id, data=json.dumps(session_data)
            )
        else:
            AIRunnerSettings.objects.create(
                name="browser_session", data=json.dumps(session_data)
            )

    def _restore_browser_session(self):
        """Restore browser session from settings."""
        try:
            settings_obj = AIRunnerSettings.objects.filter_by_first(
                name="browser_session"
            )
            if not settings_obj:
                # Only create initial tab if user explicitly wants it - don't auto-create
                return

            session_data = (
                json.loads(settings_obj.data)
                if isinstance(settings_obj.data, str)
                else settings_obj.data
            )

            # Restore private browsing mode
            self._private_browsing_mode = session_data.get(
                "private_browsing", False
            )

            # Clear existing tabs
            browser_widget = self._get_browser_tab_widget()
            if browser_widget:
                while browser_widget.count() > 0:
                    browser_widget.removeTab(0)
                self._browser_tabs.clear()

            # Restore tabs
            tabs_data = session_data.get("tabs", [])
            if tabs_data:
                for tab_data in tabs_data:
                    url = tab_data.get("url", "")
                    private = tab_data.get(
                        "private", self._private_browsing_mode
                    )
                    self.new_browser_tab(url, private)

                # Restore current tab
                current_tab_index = session_data.get("current_tab", 0)
                if (
                    browser_widget
                    and 0 <= current_tab_index < browser_widget.count()
                ):
                    browser_widget.setCurrentIndex(current_tab_index)
            # If no tabs in session, don't create any - let user create tabs manually

        except Exception as e:
            # If restore fails, log error but don't auto-create tab
            print(f"Failed to restore browser session: {e}")

    # Utility Methods

    def _show_browser_notification(self, message: str):
        """Show a browser notification message."""
        # You can customize this to use a toast notification or status bar
        print(f"Browser: {message}")

    def get_all_browser_tabs(self) -> List[BrowserWidget]:
        """Get all browser tab widgets."""
        return self._browser_tabs.copy()

    def get_current_browser_tab(self) -> Optional[BrowserWidget]:
        """Get the currently active browser tab."""
        return self._current_browser_tab

    def get_browser_tab_count(self) -> int:
        """Get the number of open browser tabs."""
        browser_widget = self._get_browser_tab_widget()
        return browser_widget.count() if browser_widget else 0

    def close_all_browser_tabs(self):
        """Close all browser tabs."""
        browser_widget = self._get_browser_tab_widget()
        if browser_widget:
            while browser_widget.count() > 1:
                self.close_browser_tab(0)
            # Clear the last tab
            self.clear_current_browser_tab()

    def browser_cleanup(self):
        """Cleanup browser resources. Call this on window close."""
        # Save session one final time
        self._save_browser_session()

        # Stop the session save timer
        if self._session_restore_timer:
            self._session_restore_timer.stop()

        # Clean up tabs
        for tab in self._browser_tabs:
            if hasattr(tab, "cleanup"):
                tab.cleanup()
