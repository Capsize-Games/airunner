# Browser Component

This module provides the browser UI and logic for AI Runner, including:

- **Private Browsing:** Toggleable mode that clears session/history and disables persistent storage.
- **Bookmarks & Folders:** Tree view for bookmarks, organized in folders. CRUD operations supported.
- **History:** List view of visited pages, with sorting/filtering and click-to-navigate.
- **Panels:** Bookmarks and history panels are shown in the left panel, only one at a time. Right panel reserved for future use.
- **Settings Sync:** All state (private browsing, bookmarks, history) is synced to the AIRunnerSettings DB table and loaded at startup.
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
- Toggle private browsing with the toolbar button.
- Open bookmarks/history panels with their respective buttons.
- Click any bookmark/history entry to navigate.
- All changes are persisted to settings automatically.

## Extending
- Add CRUD UI for bookmarks/history as needed.
- Right panel is available for future features.

---

For more details, see the main project README and architecture docs.
