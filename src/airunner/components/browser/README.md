# Browser Component

This module provides the browser UI and logic for AI Runner, including:

- **Tabbed Browsing:** Multiple tabs, each with independent session and navigation. Tabs can be opened/closed with Ctrl+T/Ctrl+W, and closed with middle mouse button on the tab bar.
- **Tab Icon & Title Updates:** Each tab displays the page favicon and title, updated automatically.
- **Session Restore:** Tabs and their state are restored on application restart.
- **Private Browsing:** Toggleable mode that clears session/history and disables persistent storage for all tabs.
- **Bookmarks & Folders:** Tree view for bookmarks, organized in folders. CRUD operations supported.
- **History:** List view of visited pages, with sorting/filtering and click-to-navigate.
- **Panels:** Bookmarks and history panels are shown in the left panel, only one at a time. Right panel reserved for future use.
- **Settings Sync:** All state (private browsing, bookmarks, history) is synced to the AIRunnerSettings DB table and loaded at startup.
- **Print Support:** Print the current page to PDF (Ctrl+P).
- **UI:** Uses `browser.ui` and `items.ui` templates. Panels are hidden by default and shown as needed.

## Key Files
- `data/settings.py`: Pydantic models for browser settings, bookmarks, history.
- `gui/widgets/browser_widget.py`: Main browser widget, panel logic, settings sync, CRUD methods.
- `gui/widgets/items_widget.py`: Generic list/tree widget for bookmarks/history.
- `gui/widgets/items_model.py`: Model helpers for bookmarks/history.
- `gui/widgets/templates/browser.ui`: Main browser UI template.
- `gui/widgets/templates/items.ui`: List view template for bookmarks/history.

## Usage
- Use the browser widget in the main app or as a standalone component.
- Open/close tabs with Ctrl+T/Ctrl+W, or close with middle mouse button on a tab.
- Toggle private browsing with the toolbar button or Shift+Ctrl+P.
- Print the current page with Ctrl+P.
- Open bookmarks/history panels with their respective buttons or shortcuts.
- Click any bookmark/history entry to navigate.
- All changes are persisted to settings automatically.
- Tabs and session state are restored on restart.

## Extending
- Add CRUD UI for bookmarks/history as needed.
- Right panel is available for future features.

---

For more details, see the main project README and architecture docs.
